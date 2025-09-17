from rest_framework import serializers
from .models import Book, Author, Category
from django.utils import timezone

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'category1', 'category2']

class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer()
    category = CategorySerializer()
    price_updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Book
        fields = '__all__'
        read_only_fields = ['price_updated_at']

    def validate(self, data):
        # 업데이트 요청일 때만 유효성 검사 실행
        if self.instance and 'price' in data:
            old_price = self.instance.price
            new_price = data['price']

            # 가격이 변경되었을 때만 검사
            if old_price != new_price:
                # 클라이언트가 가격 수정일 값을 보냈고, 그 값이 기존 값보다 이전일 경우 에러 발생
                if data.get('price_updated_at') and data['price_updated_at'] < self.instance.price_updated_at:
                    raise serializers.ValidationError('가격 수정일은 최종 가격 수정일보다 이전일 수 없습니다.')
        return data
      
    # create() 메서드 오버라이딩
    def create(self, validated_data):
        author_data = validated_data.pop('author')
        category_data = validated_data.pop('category')
        
        # 중첩된 데이터로 실제 객체 찾기 또는 생성
        author_obj, _ = Author.objects.get_or_create(**author_data)
        category_obj, _ = Category.objects.get_or_create(**category_data)
        
        # Book 객체 생성 시 외래 키 관계 연결
        # 책이 처음 생성될 때 가격 수정일 초기값 설정
        validated_data['price_updated_at'] = timezone.now()
        book = Book.objects.create(author=author_obj, category=category_obj, **validated_data)
        return book

    # update() 메서드 오버라이딩
    def update(self, instance, validated_data):
        # 중첩된 객체 업데이트 로직
        author_data = validated_data.pop('author', None)
        category_data = validated_data.pop('category', None)
        
        if author_data:
            Author.objects.update_or_create(id=instance.author.id, defaults=author_data)
        
        if category_data:
            Category.objects.update_or_create(id=instance.category.id, defaults=category_data)

         # 가격이 변경되었는지 확인하고, 변경되었으면 타임스탬프 업데이트
        if 'price' in validated_data and instance.price != validated_data['price']:
            instance.price_updated_at = timezone.now()
        
        return super().update(instance, validated_data)
    