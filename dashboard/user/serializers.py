from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from book.models import Author # Author 모델을 가져와서 사용합니다.
from django.contrib.auth import authenticate # 인증 함수 import

class RegisterSerializer(serializers.ModelSerializer):
    """
    회원가입(Register)을 위한 시리얼라이저입니다.
    - Author 모델에 등록된 작곡가만 가입 가능하도록 검증 로직을 추가했습니다.
    - 가입 시 Author 객체를 찾아 User 객체와 1:1 연결을 설정합니다.
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="이미 등록된 이메일 주소입니다.")]
    )
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True, 
        label="비밀번호 확인"
    )
    
    # 작곡가 검증을 위해 name과 contact_number를 필수로 받습니다.
    author_name = serializers.CharField(write_only=True, required=True, label="본명 (작가명)")
    contact_number = serializers.CharField(write_only=True, required=True, label="연락처")
    
    # 가입 유형을 선택합니다. 'AUTHOR' 또는 'ADMIN'
    user_type = serializers.ChoiceField(
        choices=[('AUTHOR', '작곡가'), ('ADMIN', '관리자')],
        required=True,
        write_only=True,
        label="회원 유형"
    )

    class Meta:
        model = User
        fields = ('password', 'password2', 'email', 'author_name', 'contact_number', 'user_type')

    def validate(self, attrs):
        # 1. 비밀번호 일치 검증
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})

        user_type = attrs['user_type']
        author_name = attrs['author_name']
        contact_number = attrs['contact_number']
        
        # 2. 작곡가 회원 검증 및 Author 객체 조회 (AUTHOR 타입만 해당)
        if user_type == 'AUTHOR':
            try:
                # 정확히 일치하는 Author를 찾습니다.
                author = Author.objects.get(
                    name=author_name, 
                    contact_number=contact_number
                )
            except Author.DoesNotExist:
                raise serializers.ValidationError({
                    "author_info": "입력하신 이름과 연락처에 해당하는 등록된 작곡가 정보가 없습니다."
                })
            
            # 이미 해당 Author와 연결된 User가 있는지 확인
            if author.user:
                 raise serializers.ValidationError({
                    "author_info": f"이미 {author_name} 작곡가 정보로 계정이 존재합니다. 관리자에게 문의하세요."
                })
        
        # 3. 관리자 회원 검증 (ADMIN 타입) - 이름 중복 검사
        elif user_type == 'ADMIN':
            if User.objects.filter(username=f'admin_{author_name}').exists():
                raise serializers.ValidationError({
                    "username": "이미 해당 이름의 관리자 계정이 존재합니다."
                })

        return attrs

    def create(self, validated_data):
        user_type = validated_data.pop('user_type')
        author_name = validated_data.pop('author_name')
        contact_number = validated_data.pop('contact_number')
        password = validated_data.pop('password')
        validated_data.pop('password2')
        email = validated_data['email']

        # 사용자 유형에 따라 User 객체 속성 설정
        if user_type == 'AUTHOR':
            # 작곡가는 이름 그대로 username 사용
            username = author_name
            is_staff = False
            
        else: # ADMIN
            # 관리자는 'admin_' 접두사 사용
            username = f'admin_{author_name}'
            is_staff = True
        
        # 1. User 객체 생성
        user = User.objects.create(
            username=username,
            email=email,
            # 작곡가와 관리자 모두 일단 가입 시 즉시 활성화
            is_active=True,
            is_staff=is_staff,
        )
        user.set_password(password)
        user.save()

        # 2. Author 객체에 User 연결 (AUTHOR 타입만 해당)
        if user_type == 'AUTHOR':
            # 유효성 검사에서 존재가 확인된 Author 객체를 다시 가져와 User를 연결
            try:
                author = Author.objects.get(
                    name=author_name, 
                    contact_number=contact_number
                )
                author.user = user  # User 객체 연결
                author.save()
            except Author.DoesNotExist:
                # 이 예외는 validate에서 걸러지지만, 안전을 위해 처리
                print(f"Error: Author {author_name} not found during creation.")

        return user

# --- 이메일 로그인 시리얼라이저 추가 ---

class EmailAuthTokenSerializer(serializers.Serializer):
    """
    이메일과 비밀번호를 사용하여 인증 토큰을 획득하기 위한 시리얼라이저입니다.
    """
    email = serializers.CharField(label="Email")
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    token = serializers.CharField(label="Token", read_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # 1. 이메일을 사용하여 사용자 이름을 찾습니다.
            try:
                user_instance = User.objects.get(email__iexact=email)
                username = user_instance.username
            except User.DoesNotExist:
                # 이메일로 사용자를 찾지 못한 경우 인증 실패
                msg = ('제공된 이메일로 계정을 찾을 수 없습니다.')
                raise serializers.ValidationError(msg, code='authorization')

            # 2. 찾은 username과 password를 사용하여 인증을 시도합니다.
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            if not user:
                # 사용자 인증 실패 (비밀번호 오류 등)
                msg = ('이메일 또는 비밀번호가 올바르지 않습니다.')
                raise serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                # 비활성화된 사용자
                msg = ('이 사용자 계정은 비활성화되어 있습니다.')
                raise serializers.ValidationError(msg, code='authorization')

        else:
            msg = ('이메일과 비밀번호를 모두 입력해야 합니다.')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs
    