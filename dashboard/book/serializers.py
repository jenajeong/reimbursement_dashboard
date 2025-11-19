# book/serializers.py

import re
import datetime
from rest_framework import serializers
from .models import Book, Author, Composer, ComposerWork, PriceHistory

# --- 1. 책 종류 매핑 필드 (변경 없음) ---
class BookTypeField(serializers.Field):
    BOOK_TYPE_MAP = {'일반': 'GEN', '피스': 'PCS', '총보': 'SCO'}
    REVERSE_BOOK_TYPE_MAP = {v: k for k, v in BOOK_TYPE_MAP.items()}
    def to_representation(self, value):
        return self.REVERSE_BOOK_TYPE_MAP.get(value, value)
    def to_internal_value(self, data):
        value = self.BOOK_TYPE_MAP.get(data)
        if value is None:
            if data in self.REVERSE_BOOK_TYPE_MAP: return data
            valid_options = ", ".join(self.BOOK_TYPE_MAP.keys())
            raise serializers.ValidationError(f"'{data}'는 유효한 책 종류가 아닙니다. ({valid_options} 중 하나여야 함)")
        return value

# --- 2. 읽기/중첩 전용 시리얼라이저 (변경 없음) ---
class AuthorSerializer(serializers.ModelSerializer):
    class Meta: model = Author; fields = ['id', 'name']

class ComposerSerializer(serializers.ModelSerializer):
    class Meta: model = Composer; fields = ['id', 'name', 'date_of_birth', 'contact_number']

class PriceHistorySerializer(serializers.ModelSerializer):
    price = serializers.IntegerField(min_value=0)
    price_updated_at = serializers.DateTimeField(required=False)
    class Meta: model = PriceHistory; fields = ['price', 'price_updated_at', 'is_latest']

class ComposerWorkReadSerializer(serializers.ModelSerializer):
    composer = ComposerSerializer(read_only=True)
    class Meta: model = ComposerWork; fields = ['id', 'composer', 'number_of_songs', 'royalty_percentage']

class ComposerWorkWriteSerializer(serializers.Serializer): 
    composer_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    contact_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    
    number_of_songs = serializers.IntegerField(min_value=1, required=True)
    royalty_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=True)

    def validate_name(self, value):
        if not value: return value 
        if not re.match(r'^[가-힣a-zA-Z0-9\s\(\)\-\.]+$', value.strip()):
            raise serializers.ValidationError("작곡가 이름은 한글, 영문, 숫자, 공백, 특수문자(-, ., (, ))만 가능합니다.")
        return value.strip()
    
    def validate(self, data):
        composer_id = data.get('composer_id')
        name = data.get('name')
        contact = data.get('contact_number')

        if composer_id:
            pass 
        elif not name:
             raise serializers.ValidationError("새 작곡가를 추가하려면 '작곡가명'이 필요합니다.")
        elif not contact:
            raise serializers.ValidationError("새 작곡가를 추가하려면 '작곡가명'과 '연락처'가 모두 필요합니다.")
        
        return data


# --- 4. 메인 시리얼라이저 (Book) ---
class BookSerializer(serializers.ModelSerializer):
    # --- 읽기 전용 필드 (변경 없음) ---
    authors_read = AuthorSerializer(many=True, read_only=True, source='authors')
    price_histories = PriceHistorySerializer(many=True, read_only=True)
    composers_read = ComposerWorkReadSerializer(source='composerwork_set', many=True, read_only=True)

    # --- [핵심 수정] 쓰기 전용 필드 이름을 JSON 키와 일치시킴 ---
    author_names = serializers.ListField( # authors -> author_names 변경
        child=serializers.CharField(max_length=100),
        write_only=True, required=False
    )
    composers_write = ComposerWorkWriteSerializer( # composers_data -> composers_write 변경
        many=True, write_only=True, required=False
    )
    initial_price_history_write = PriceHistorySerializer( # initial_price_history -> initial_price_history_write 변경
        many=True, write_only=True, required=False
    )

    # --- 공통 필드 ---
    book_type = BookTypeField(required=False)
    category1 = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category2 = serializers.CharField(required=False, allow_blank=True, max_length=100)
    title_korean = serializers.CharField(required=False) 
    
    class Meta:
        model = Book
        fields = [
            'id', 'title_korean', 'title_original', 'publisher',
            'book_type', 'category1', 'category2',
            'authors_read', 'price_histories', 'composers_read', # 읽기용
            'author_names', 'composers_write', 'initial_price_history_write' # 쓰기용 (이름 변경됨)
        ]

    # --- 생성 로직 (Create) ---
    def create(self, validated_data):
        # [수정] 변경된 키 이름으로 데이터 추출 (pop)
        author_data = validated_data.pop('author_names', [])
        composers_data = validated_data.pop('composers_write', [])
        initial_price_history_data = validated_data.pop('initial_price_history_write', [])
        
        # 필수 체크
        if not author_data: raise serializers.ValidationError({"author_names": "저자는 최소 1명 이상 필요합니다."})
        if not composers_data: raise serializers.ValidationError({"composers_write": "작곡가는 최소 1명 이상 필요합니다."})
        if not initial_price_history_data: raise serializers.ValidationError({"initial_price_history_write": "초기 가격 정보가 필요합니다."})

        # 책 생성 (카테고리는 CharField이므로 validated_data에 포함되어 자동 저장됨)
        try: 
            book = Book.objects.create(**validated_data)
        except Exception as e: 
            raise serializers.ValidationError(f"책 생성 오류: {e}")
        
        # 저자 연결 (이름으로 찾거나 생성)
        authors_to_set = []
        for name in author_data:
            author, _ = Author.objects.get_or_create(name=name)
            authors_to_set.append(author)
        book.authors.set(authors_to_set)
        
        # 가격 정보 저장
        price_data = initial_price_history_data[0]
        updated_at = price_data.get('price_updated_at', datetime.datetime.now(datetime.timezone.utc))
        PriceHistory.objects.create(book=book, price=price_data['price'], price_updated_at=updated_at, is_latest=True)
        
        # 작곡가 정보 저장
        for work_data in composers_data:
            try:
                composer = self._get_or_create_composer(work_data) 
                ComposerWork.objects.create(
                    book=book,
                    composer=composer,
                    number_of_songs=work_data['number_of_songs'],
                    royalty_percentage=work_data['royalty_percentage']
                )
            except Exception as e: 
                raise serializers.ValidationError(f"작곡가 처리 오류: {e}")

        return book

    # --- 수정 로직 (Update) ---
    def update(self, instance, validated_data):
        # [수정] 변경된 키 이름으로 데이터 추출
        author_data = validated_data.pop('author_names', None)
        composers_data = validated_data.pop('composers_write', None)
        initial_price_history_data = validated_data.pop('initial_price_history_write', None)
        
        instance = super().update(instance, validated_data)

        # 저자 업데이트
        if author_data is not None:
            authors_to_set = []
            for name in author_data:
                author, _ = Author.objects.get_or_create(name=name) 
                authors_to_set.append(author)
            instance.authors.set(authors_to_set)
        
        # 가격 업데이트
        if initial_price_history_data:
            new_price_data = initial_price_history_data[0]
            new_price = new_price_data.get('price')
            if new_price is not None:
                latest_price_obj = instance.price_histories.filter(is_latest=True).first()
                if not latest_price_obj or latest_price_obj.price != new_price:
                    instance.price_histories.update(is_latest=False)
                    PriceHistory.objects.create(
                        book=instance,
                        price=new_price,
                        price_updated_at=new_price_data.get('price_updated_at', datetime.datetime.now(datetime.timezone.utc)),
                        is_latest=True
                    )

        # 작곡가 업데이트
        if composers_data is not None:
            instance.composerwork_set.all().delete() 
            for work_data in composers_data:
                try:
                    composer = self._get_or_create_composer(work_data) 
                    ComposerWork.objects.create(
                        book=instance,
                        composer=composer,
                        number_of_songs=work_data['number_of_songs'],
                        royalty_percentage=work_data['royalty_percentage']
                    )
                except Exception as e:
                     raise serializers.ValidationError(f"작곡가 처리 오류: {e}")

        return instance

    def _get_or_create_composer(self, work_data):
        # ... (기존 로직 유지) ...
        composer_id = work_data.get('composer_id')
        composer_name = work_data.get('name', '').strip()
        date_of_birth = work_data.get('date_of_birth')

        if composer_id:
            try: return Composer.objects.get(pk=composer_id)
            except Composer.DoesNotExist: raise ValueError(f"ID {composer_id}의 작곡가를 찾을 수 없습니다.")
        
        if not composer_name: raise ValueError("작곡가 이름이 비어 있습니다.")
        
        # [중요] date_of_birth가 없으면 기본값 처리하거나 에러 (여기서는 생성 시 필수이므로 유지)
        if not date_of_birth: 
             raise ValueError(f"'{composer_name}' 작곡가의 생년월일 정보가 필요합니다.")

        composer, created = Composer.objects.get_or_create(
            name=composer_name,
            date_of_birth=date_of_birth,
            defaults={'contact_number': work_data.get('contact_number', '')} 
        )
        return composer

# --- 목록 조회용 시리얼라이저 (변경 없음) ---
class BookListSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    current_price = serializers.SerializerMethodField()
    book_type = BookTypeField()
    class Meta:
        model = Book
        fields = ['id', 'title_korean', 'publisher', 'book_type', 'category1', 'category2', 'authors', 'current_price']
    def get_current_price(self, obj):
        latest_price = obj.price_histories.filter(is_latest=True).first()
        return latest_price.price if latest_price else None

