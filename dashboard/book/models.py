# models.py

from django.db import models
from datetime import date
from django.conf import settings
from django.contrib.auth.models import User

# 1. Author 모델 (기존 모델 유지 또는 이름 변경)
class Author(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='author_profile')
    name = models.CharField(max_length=100, verbose_name="저자 이름")
    contact_number = models.CharField(max_length=20, blank=True, verbose_name="연락처")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="생년월일")

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "저자"
        verbose_name_plural = "저자 목록"

# ==================== NEW/MODIFIED CODE START ====================

# 2. Composer 모델 (새로 추가)
# 작곡가 정보를 저장하는 모델입니다.
class Composer(models.Model):
    name = models.CharField(max_length=100, verbose_name="작곡가 이름")
    contact_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="연락처")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="생년월일")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "작곡가"
        verbose_name_plural = "작곡가 목록"

# =================================================================

class Category(models.Model):
    category1 = models.CharField(max_length=100, verbose_name='대분류')
    category2 = models.CharField(max_length=100, verbose_name='소분류')

    def __str__(self):
        return f'{self.category1} > {self.category2}'

class Book(models.Model):
    BOOK_TYPES = [
        ('GEN', '일반'),
        ('PCS', '피스'),
        ('SCO', '총보'),
    ]

    # --- 기존 Author 관계 ---
    authors = models.ManyToManyField(Author, through='AuthorWork', related_name='books', verbose_name="저자")
    
    # ==================== NEW/MODIFIED CODE START ====================

    # --- 새로 추가된 Composer 관계 ---
    # Composer 모델과 ManyToMany 관계를 맺고, ComposerWork를 중간 모델로 사용합니다.
    composers = models.ManyToManyField(Composer, through='ComposerWork', related_name='composed_books', verbose_name="작곡가")

    # =================================================================

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, verbose_name='카테고리', null=True)
    title_korean = models.CharField(max_length=200, verbose_name='책 제목 (한글)')
    title_original = models.CharField(max_length=200, verbose_name='책 제목 (원제)', null=True, blank=True)
    book_type = models.CharField(max_length=3, choices=BOOK_TYPES, default='GEN', verbose_name='책 종류')
    subtitle = models.CharField(max_length=200, verbose_name='부제', null=True, blank=True)
    publication_date = models.DateField(verbose_name="출판일", default=date.today)
    publisher = models.CharField(max_length=100, verbose_name='출판사', default='와이즈성가')

    def __str__(self):
        return self.title_korean

class PriceHistory(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='price_histories', verbose_name='책')
    price = models.IntegerField(verbose_name='가격')
    price_updated_at = models.DateTimeField(verbose_name='가격 변경일')

    class Meta:
        ordering = ['-price_updated_at']

    def __str__(self):
        return f'{self.book.title_korean} - {self.price} ({self.price_updated_at})'

class AuthorWork(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name="저자")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="책")
    # 'contribution_type' 같은 필드를 추가하여 '편곡', '작사' 등을 구분할 수도 있습니다.
    
    class Meta:
        verbose_name = "저자 작업"
        verbose_name_plural = "저자 작업 목록"
        unique_together = ('author', 'book')

    def __str__(self):
        return f'{self.author.name} - {self.book.title_korean}'

# ==================== NEW/MODIFIED CODE START ====================

# 3. ComposerWork 중간 모델 (새로 추가)
# 작곡가와 책의 다대다 관계에 '곡 수' 정보를 추가하는 중간 모델입니다.
class ComposerWork(models.Model):
    composer = models.ForeignKey(Composer, on_delete=models.CASCADE, verbose_name="작곡가")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="책")
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
        # 한 작곡가가 한 책에 대해 중복으로 입력되지 않도록 유니크 제약조건 추가
        unique_together = ('composer', 'book')

    def __str__(self):
        return f'{self.composer.name} - {self.book.title_korean} ({self.number_of_songs}곡) , {self.royalty_percentage}%'

# =================================================================