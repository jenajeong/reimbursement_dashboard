from rest_framework import serializers
from .models import Book, Author, Category, PriceHistory
from django.utils import timezone

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'category1', 'category2']

class BookListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    category = CategorySerializer()
    
    class Meta:
        model = Book
        # 목록 페이지에 필요한 필드만 포함
        fields = ['id', 'title_korean', 'author', 'category', 'price']

# 가격 변동 기록을 위한 시리얼라이저 (유효성 검사 로직 포함)
class PriceHistorySerializer(serializers.ModelSerializer):
    price_updated_at = serializers.DateTimeField(required=True)

    class Meta:
        model = PriceHistory
        fields = ['price', 'price_updated_at']

    def validate_price_updated_at(self, value):
        # 1. 오늘을 넘어서는 안 된다는 유효성 검사
        if value > timezone.now():
            raise serializers.ValidationError('가격 변동일은 현재 시각보다 미래일 수 없습니다.')

        # 2. 직전 정보보다 작아서는 안 된다는 유효성 검사
        book = self.context.get('book')
        if book:
            latest_history = book.price_histories.first()
            if latest_history and value < latest_history.price_updated_at:
                raise serializers.ValidationError('가격 변동일은 이전 기록보다 빠를 수 없습니다.')
        return value
    
        
class BookDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    category = CategorySerializer()
    price_histories = PriceHistorySerializer(many=True, required=False)

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = []

    def create(self, validated_data):
        author_data = validated_data.pop('author')
        category_data = validated_data.pop('category')
        # pop() 시 기본값으로 None을 지정하여 Key Error 방지
        price_histories_data = validated_data.pop('price_histories', None)

        author_obj, _ = Author.objects.get_or_create(**author_data)
        category_obj, _ = Category.objects.get_or_create(**category_data)
        
        book = Book.objects.create(author=author_obj, category=category_obj, **validated_data)
        
        if price_histories_data:
            PriceHistory.objects.create(book=book, **price_histories_data[0])
            
        return book

    def update(self, instance, validated_data):
        author_data = validated_data.pop('author', None)
        category_data = validated_data.pop('category', None)
        price_histories_data = validated_data.pop('price_histories', None)

        if author_data:
            Author.objects.update_or_create(id=instance.author.id, defaults=author_data)
        
        if category_data:
            Category.objects.update_or_create(id=instance.category.id, defaults=category_data)

        if price_histories_data:
            new_history_data = price_histories_data[0]
            latest_history = instance.price_histories.first()

            # 새로운 가격이 이전과 다를 때만 모든 유효성 검사 및 기록을 생성합니다.
            if not latest_history or latest_history.price != new_history_data['price']:
                history_serializer = PriceHistorySerializer(data=new_history_data, context={'book': instance})
                history_serializer.is_valid(raise_exception=True)
                PriceHistory.objects.create(book=instance, **new_history_data)
            else:
                 # 가격은 그대로인데, 가격 변동일만 변경하려는 시도를 방지합니다.
                 # 이 로직은 `price_updated_at`가 달라진 경우에만 실행됩니다.
                 if latest_history.price_updated_at != new_history_data['price_updated_at']:
                    raise serializers.ValidationError({
                        'price_histories': '가격 변동일만 수정할 수 없습니다.'
                    })
        
        return super().update(instance, validated_data)

