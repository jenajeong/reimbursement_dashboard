from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
import datetime # price_updated_at의 기본값을 위해 import

# --- 1. 저자 모델 ---
# 요청: index(자동), 저자 이름
# (책 참조는 Book 모델의 M2M 필드로 구현)
class Author(models.Model):
    name = models.CharField(max_length=100, verbose_name="저자 이름")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "저자"
        verbose_name_plural = "저자 목록"


# --- 2. 작곡가 모델 ---
# 요청: index(자동), 작곡가 이름, 태어난 날짜, 연락처
class Composer(models.Model):
    name = models.CharField(max_length=100, verbose_name="작곡가 이름")
    # [수정] default 값을 추가하여 non-nullable 마이그레이션 오류 해결
    date_of_birth = models.DateField(verbose_name="생년월일", default=datetime.date(1900, 1, 1))
    # [수정] null=True를 제거하는 대신, default=''를 추가합니다.
    contact_number = models.CharField(max_length=20, verbose_name="연락처", default='') 

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "작곡가"
        verbose_name_plural = "작곡가 목록"


# --- 3. 책 모델 ---
# 요청: 책 종류, 저자이름(참조), 카테고리1, 카테고리2, 출판사, 책제목(한글), 책제목(원어)
class Book(models.Model):
    # 책 종류
    BOOK_TYPES = [
        ('GEN', '일반'),
        ('PCS', '피스'),
        ('SCO', '총보'),
    ]
    book_type = models.CharField(max_length=3, choices=BOOK_TYPES, default='GEN', verbose_name='책 종류')
    
    # 저자이름 (참조) - AuthorWork 없이 직접 M2M 연결
    authors = models.ManyToManyField(
        'Author', 
        related_name='books', 
        verbose_name="저자",
        blank=True # 저자가 없을 수도 있으므로 blank=True
    )

    # 카테고리1, 카테고리2 (기존 Category 모델 대신 직접 필드로 추가)
    category1 = models.CharField(max_length=100, verbose_name='대분류', null=True, blank=True)
    category2 = models.CharField(max_length=100, verbose_name='소분류', null=True, blank=True)
    
    # 기타 필드
    publisher = models.CharField(max_length=100, verbose_name='출판사', null=True, blank=True)
    title_korean = models.CharField(max_length=200, verbose_name='책 제목 (한글)')
    title_original = models.CharField(max_length=200, verbose_name='책 제목 (원제)', null=True, blank=True)

    # ComposerWork와의 연결을 위해 M2M 필드 유지 (ComposerWork에서 필요)
    composers = models.ManyToManyField(
        'Composer', 
        through='ComposerWork', 
        related_name='composed_books', 
        verbose_name="작곡가",
        blank=True
    )
    
    def __str__(self):
        return self.title_korean
        
    class Meta:
        verbose_name = "책"
        verbose_name_plural = "책 목록"


# --- 4. 작곡가 작업 (중간 모델) ---
# 요청: index(자동), 작곡가 이름(참조), 책이름(참조), 곡 수, 저작권료
class ComposerWork(models.Model):
    composer = models.ForeignKey('Composer', on_delete=models.CASCADE, verbose_name="작곡가")
    book = models.ForeignKey('Book', on_delete=models.CASCADE, verbose_name="책")
    number_of_songs = models.PositiveIntegerField(default=1, verbose_name="곡 수")
    royalty_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00, 
        verbose_name="저작권료 (%)"
    )

    class Meta:
        verbose_name = "작곡가 작업"
        verbose_name_plural = "작곡가 작업 목록"
        unique_together = ('composer', 'book') # 한 책에 작곡가가 중복으로 추가되는 것 방지

    def __str__(self):
        return f'{self.composer.name} - {self.book.title_korean} ({self.number_of_songs}곡)'


# --- 5. 가격 변경 이력 ---
# 요청: 책 이름(참조), 가격, 가격 변경일, 마지막 변경(T/F)
class PriceHistory(models.Model):
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='price_histories', verbose_name='책')
    price = models.IntegerField(verbose_name='가격')
    price_updated_at = models.DateTimeField(verbose_name='가격 변경일', default=datetime.datetime.now)
    
    # 마지막 변경(T/F) - 이 가격이 현재 최신 가격인지 여부
    is_latest = models.BooleanField(default=False, verbose_name="최신 가격 여부(T/F)")

    class Meta:
        # 최신순으로 정렬
        ordering = ['-price_updated_at'] 
        verbose_name = "가격 이력"
        verbose_name_plural = "가격 이력 목록"

    def __str__(self):
        return f'{self.book.title_korean} - {self.price} ({self.price_updated_at})'
