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

# --- 3. 쓰기(Create/Update)용 중첩 시리얼라이저 (변경 없음) ---
class ComposerWorkWriteSerializer(serializers.Serializer): 
    composer_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    number_of_songs = serializers.IntegerField(min_value=1, required=True)
    royalty_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=True)

    def validate_name(self, value):
        if not value: return value # Update 시 비어있을 수 있음
        if not re.match(r'^[가-힣a-zA-Z0-9\s\(\)\-\.]+$', value.strip()):
            raise serializers.ValidationError("작곡가 이름은 한글, 영문, 숫자, 공백, 특수문자(-, ., (, ))만 가능합니다.")
        return value.strip()
    
    def validate(self, data):
        """ composer_id 또는 (name + contact_number)가 있는지 확인 """
        composer_id = data.get('composer_id')
        name = data.get('name')
        contact = data.get('contact_number')

        if composer_id:
            data.pop('name', None)
            data.pop('contact_number', None)
            if not Composer.objects.filter(pk=composer_id).exists():
                raise serializers.ValidationError(f"ID {composer_id}의 작곡가가 존재하지 않습니다.")
        elif not name or not contact:
            # 2. ID가 없으면, 이름과 연락처가 모두 필수
            raise serializers.ValidationError("새 작곡가를 추가하려면 '작곡가명'과 '연락처'가 모두 필요합니다.")
        
        return data


# --- 4. 메인 시리얼라이저 (Book) ---
class BookSerializer(serializers.ModelSerializer):
    # --- 읽기 전용 필드 (변경 없음) ---
    authors_read = AuthorSerializer(many=True, read_only=True, source='authors')
    price_histories = PriceHistorySerializer(many=True, read_only=True)
    composers_read = ComposerWorkReadSerializer(source='composerwork_set', many=True, read_only=True)

    # --- [수정] 쓰기 전용 필드 (JS 키 이름과 필드 이름을 일치시킴) ---
    # (필드 이름: authors, composers_data, initial_price_history)
    authors = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True, required=False # PATCH는 필수가 아님
    )
    composers_data = ComposerWorkWriteSerializer(
        many=True, write_only=True, required=False
    )
    initial_price_history = PriceHistorySerializer(
        many=True, write_only=True, required=False # PATCH는 필수가 아님
    )

    # --- 공통 필드 (PATCH를 위해 required=False로 변경) ---
    book_type = BookTypeField(required=False)
    category1 = serializers.CharField(required=False, allow_blank=True, max_length=100)
    category2 = serializers.CharField(required=False, allow_blank=True, max_length=100)
    title_korean = serializers.CharField(required=False) 
    
    class Meta:
        model = Book
        fields = [
            'id', 'title_korean', 'title_original', 'publisher',
            'book_type', 'category1', 'category2',
            'authors_read', 'price_histories', 'composers_read', # 읽기
            'authors', 'composers_data', 'initial_price_history' # 쓰기
        ]

    # --- 유효성 검사 (Validation) ---
    def validate_korean_english_special(self, value, field_name="필드"):
        value = (value or "").strip() 
        if not value: return value # 빈 값 허용 (Update이므로)
        if not re.match(r'^[가-힣a-zA-Z0-9\s\(\)\-\.]+$', value):
            raise serializers.ValidationError(f"{field_name} 값은 한글, 영문, 숫자, 공백, 특수문자(-, ., (, ))만 가능합니다.")
        return value
    def validate_title_korean(self, value):
        return self.validate_korean_english_special(value, "책 제목(한글)")
    def validate_authors(self, author_names_list):
        if not author_names_list: return [] # Update 시 빈 리스트 허용
        valid_authors = []
        for name in author_names_list:
            stripped_name = name.strip()
            if not stripped_name: continue 
            if not re.match(r'^[가-힣a-zA-Z0-9\s\(\)\-\.]+$', stripped_name): # [수정] 저자 이름도 특수문자 허용
                raise serializers.ValidationError(f"저자 이름 '{name}'은(는) 유효한 문자(한글,영문,숫자,공백,-,.,(,))만 사용 가능합니다.")
            valid_authors.append(stripped_name)
        return valid_authors
    def validate_category1(self, value):
        return self.validate_korean_english_special(value, "카테고리1")
    def validate_category2(self, value):
        return self.validate_korean_english_special(value, "카테고리2")
    def validate_composers_data(self, composers_data_list):
        if not composers_data_list: return [] # Update 시 빈 리스트 허용
        return composers_data_list
    def validate_initial_price_history(self, value):
        if not value: return [] # Update 시 빈 리스트 허용
        if len(value) != 1:
            raise serializers.ValidationError("가격 정보는 1개만 제공되어야 합니다.")
        if value[0].get('price') is None:
             raise serializers.ValidationError("가격(price) 필드가 필요합니다.")
        return value

    # --- 생성 로직 (Create) ---
    def create(self, validated_data):
        # Create 시에는 필수 필드 재검증
        author_data = validated_data.pop('authors')
        composers_data = validated_data.pop('composers_data')
        initial_price_history_data = validated_data.pop('initial_price_history')
        
        if not author_data: raise serializers.ValidationError({"authors": "저자는 최소 1명 이상 필요합니다."})
        if not composers_data: raise serializers.ValidationError({"composers_data": "작곡가는 최소 1명 이상 필요합니다."})
        if not initial_price_history_data: raise serializers.ValidationError({"initial_price_history": "초기 가격 정보가 필요합니다."})

        try: book = Book.objects.create(**validated_data)
        except Exception as e: raise serializers.ValidationError(f"책 생성 오류: {e}")
        
        authors_to_set = []
        for name in author_data:
            author, _ = Author.objects.get_or_create(name=name)
            authors_to_set.append(author)
        book.authors.set(authors_to_set)
        
        price_data = initial_price_history_data[0]
        updated_at = price_data.get('price_updated_at', datetime.datetime.now(datetime.timezone.utc))
        PriceHistory.objects.create( book=book, price=price_data['price'], price_updated_at=updated_at, is_latest=True )
        
        for work_data in composers_data:
            try:
                # _get_or_create_composer가 composer_id 또는 name/dob로 처리
                composer = self._get_or_create_composer(work_data) 
                ComposerWork.objects.create(
                    book=book,
                    composer=composer,
                    number_of_songs=work_data['number_of_songs'],
                    royalty_percentage=work_data['royalty_percentage']
                )
            except Exception as e: raise serializers.ValidationError({f"composers_data ({work_data.get('name', 'ID: '+str(work_data.get('composer_id')))})": f"처리 오류: {e}"})

        return book

    # --- [수정] 수정 로직 (Update) ---
    def update(self, instance, validated_data):
        author_data = validated_data.pop('authors', None)
        composers_data = validated_data.pop('composers_data', None)
        initial_price_history_data = validated_data.pop('initial_price_history', None)
        
        instance = super().update(instance, validated_data)

        # 3. 저자 처리 (전체 교체)
        if author_data is not None: # 키가 존재하면 (빈 리스트 포함)
            authors_to_set = []
            for name in author_data:
                author, _ = Author.objects.get_or_create(name=name) 
                authors_to_set.append(author)
            instance.authors.set(authors_to_set) # 빈 리스트면 M2M 연결 모두 해제
        
        # 4. 가격 처리 (변경 시에만 새 이력 추가)
        if initial_price_history_data: # 가격 정보가 제공된 경우
            new_price_data = initial_price_history_data[0]
            new_price = new_price_data.get('price')
            
            if new_price is not None:
                latest_price_obj = instance.price_histories.filter(is_latest=True).first()
                
                # 기존 가격이 없거나, 새 가격이 기존 최신 가격과 다를 때만
                if not latest_price_obj or latest_price_obj.price != new_price:
                    instance.price_histories.update(is_latest=False) # 기존 내역 '최신' 끄기
                    PriceHistory.objects.create(
                        book=instance,
                        price=new_price,
                        price_updated_at=new_price_data.get('price_updated_at', datetime.datetime.now(datetime.timezone.utc)),
                        is_latest=True
                    )
                # [수정] 가격이 같더라도, JS가 보낸 시간이 DB 시간과 다르면 시간만 업데이트 (선택적)
                elif latest_price_obj and latest_price_obj.price == new_price:
                    new_time = new_price_data.get('price_updated_at', datetime.datetime.now(datetime.timezone.utc))
                    # (시간 비교 로직 추가 - 여기서는 생략)
                    pass


        # 5. 작곡가/작업 처리 (전체 교체)
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
                     raise serializers.ValidationError(f"작곡가 '{work_data.get('name', work_data.get('composer_id'))}' 처리 중 오류: {e}")

        return instance

    def _get_or_create_composer(self, work_data):
        """ [Helper] composer_id 또는 (name/dob)로 작곡가 객체를 가져오거나 생성 """
        composer_id = work_data.get('composer_id')
        composer_name = work_data.get('name', '').strip()
        date_of_birth = work_data.get('date_of_birth') # [수정]

        if composer_id:
            # 1. ID가 있으면, 해당 작곡가 반환
            try:
                return Composer.objects.get(pk=composer_id)
            except Composer.DoesNotExist:
                raise ValueError(f"ID {composer_id}의 작곡가를 찾을 수 없습니다.")
        
        # 2. ID가 없으면, 이름과 생년월일로 찾거나 생성
        if not composer_name: raise ValueError("작곡가 이름이 비어 있습니다.")
        if not date_of_birth: # [수정] 생년월일 검증
             raise ValueError(f"'{composer_name}' 작곡가의 유효한 생년월일 정보가 필요합니다.")

        composer, created = Composer.objects.get_or_create(
            name=composer_name,
            date_of_birth=date_of_birth, # 이름과 생년월일이 모두 같아야 동일인
            defaults={'contact_number': ''} # [수정] 연락처는 기본값으로
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

