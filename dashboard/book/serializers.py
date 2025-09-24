from rest_framework import serializers
from .models import Book, Author, Category, PriceHistory, AuthorWork
from django.utils import timezone
import re
from datetime import date
from django.db.models import Sum

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

class AuthorSerializer(serializers.ModelSerializer):
    # 저자와 책의 연결을 위한 ManyToMany 필드
    works = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Author
        fields = ['id', 'name', 'contact_number', 'date_of_birth', 'works']

    def validate_name(self, value):
        if not re.match(r'^[가-힣a-zA-Z]+$', value):
            raise serializers.ValidationError("이름에는 한글, 영문만 사용할 수 있습니다.")
        return value

    def validate_contact_number(self, value):
        number_only = value.replace('-', '')
        if len(number_only) > 11:
            raise serializers.ValidationError("전화번호는 총 11자리를 초과할 수 없습니다.")
        pattern = re.compile(r'^\d{2,3}-\d{3,4}-\d{4}$')
        if not pattern.match(value):
            raise serializers.ValidationError("전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)")
        return value

    def validate_date_of_birth(self, value):
        if value > date.today():
            raise serializers.ValidationError("생년월일은 미래 날짜일 수 없습니다.")
        return value
    
    def create(self, validated_data):
        works_data = validated_data.pop('works', [])
        author = Author.objects.create(**validated_data)
        
        for work in works_data:
            book_id = work.get('book_id')
            number_of_songs = work.get('number_of_songs', 1)
            
            try:
                book = Book.objects.get(id=book_id)
                AuthorWork.objects.create(
                    author=author, 
                    book=book, 
                    number_of_songs=number_of_songs
                )
            except Book.DoesNotExist:
                raise serializers.ValidationError(f"Book with id {book_id} does not exist.")
        
        return author

    def update(self, instance, validated_data):
        works_data = validated_data.pop('works', None)
        
        instance.name = validated_data.get('name', instance.name)
        instance.contact_number = validated_data.get('contact_number', instance.contact_number)
        instance.date_of_birth = validated_data.get('date_of_birth', instance.date_of_birth)
        instance.save()
        
        if works_data is not None:
            # 기존 저자의 작업물 모두 삭제 후 새로 생성
            instance.authorwork_set.all().delete()
            for work in works_data:
                book_id = work.get('book_id')
                number_of_songs = work.get('number_of_songs', 1)
                
                try:
                    book = Book.objects.get(id=book_id)
                    AuthorWork.objects.create(
                        author=instance,
                        book=book,
                        number_of_songs=number_of_songs
                    )
                except Book.DoesNotExist:
                    raise serializers.ValidationError(f"Book with id {book_id} does not exist.")
        
        return instance

class AuthorListSerializer(serializers.ModelSerializer):
    total_books = serializers.SerializerMethodField()
    total_songs = serializers.SerializerMethodField()
    
    class Meta:
        model = Author
        fields = ['id', 'name', 'date_of_birth', 'contact_number', 'total_books', 'total_songs']
    
    def get_total_books(self, obj):
        # context에서 기간 정보를 가져옵니다.
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        # 필터링할 AuthorWork 쿼리셋을 준비합니다.
        qs = obj.authorwork_set.all()

        # 기간 정보가 있다면 필터링을 적용합니다.
        if start_date:
            qs = qs.filter(book__publication_date__gte=start_date)
        if end_date:
            qs = qs.filter(book__publication_date__lte=end_date)
            
        return qs.count()

    def get_total_songs(self, obj):
        # context에서 기간 정보를 가져옵니다.
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        # 'order' 모델이 없어 'book__publication_date'를 기준으로 필터링합니다.
        qs = obj.authorwork_set.all()
        
        # 기간 정보가 있다면 필터링을 적용합니다.
        if start_date:
            qs = qs.filter(book__publication_date__gte=start_date)
        if end_date:
            qs = qs.filter(book__publication_date__lte=end_date)
            
        total = qs.aggregate(Sum('number_of_songs'))['number_of_songs__sum']
        return total if total is not None else 0

class AuthorDetailSerializer(serializers.ModelSerializer):
    books_authored = serializers.SerializerMethodField()
    
    class Meta:
        model = Author
        fields = ['id', 'name', 'date_of_birth', 'contact_number', 'books_authored']
        
    def get_books_authored(self, obj):
        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')
        
        # 'Order' 모델이 있다고 가정하고 필터링을 진행합니다.
        # Order 모델이 Book과 연결되어 있고 'order_date' 필드가 있다고 가정합니다.
        qs = obj.authorwork_set.all()
        
        if start_date and end_date:
            qs = qs.filter(book__order__order_date__range=[start_date, end_date]).distinct()

        results = []
        for author_work in qs:
            book = author_work.book
            
            # 해당 책의 총 판매량을 계산 (Order 모델이 있다고 가정)
            total_sales = 0
            if start_date and end_date:
                # 여기서 Order 모델을 사용해 판매량을 집계합니다.
                # 예: total_sales = book.order_set.filter(order_date__range=[start_date, end_date]).count()
                pass # 실제 로직은 Order 모델 구조에 따라 달라집니다.
            
            results.append({
                'book_id': book.id,
                'book_title': book.title_korean,
                'number_of_songs': author_work.number_of_songs,
                'total_sales': total_sales
            })
            
        return results
    