from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100, verbose_name="name")
    contact_number = models.CharField(max_length=20, blank=True, verbose_name="contact_number")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="date_of_birth")

    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Author_list"

class Category(models.Model):
    category1 = models.CharField(max_length=100, verbose_name='category1')
    category2 = models.CharField(max_length=100, verbose_name='category2')

    def __str__(self):
        return f'{self.category1} > {self.category2}'

class Book(models.Model):
    
    BOOK_TYPES = [
        ('GEN', '일반'),
        ('PCS', '피스'),
        ('SCO', '총보'),
    ]

    # 저자 ID (ForeignKey)
    author = models.ManyToManyField(Author, through='AuthorWork', related_name='books', verbose_name="Authors")
    # 카테고리 ID (ForeignKey)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, verbose_name='category', null=True)

    title_korean = models.CharField(max_length=200, verbose_name='title_korean')
    title_original = models.CharField(max_length=200, verbose_name='title_original', null=True, blank=True)
    book_type = models.CharField(max_length=3, choices=BOOK_TYPES, default='GEN', verbose_name='book_type')
    subtitle = models.CharField(max_length=200, verbose_name='subtitle', null=True, blank=True)
    publication_date = models.DateField(verbose_name="publication_date")

    def __str__(self):
        return self.title_korean

class PriceHistory(models.Model):
    # Book 모델과 연결
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='price_histories', verbose_name='book')
    price = models.IntegerField(verbose_name='price')
    price_updated_at = models.DateTimeField(verbose_name='price_updated_at')

    class Meta:
        # 가장 최근 가격 기록이 항상 먼저 오도록 내림차순 정렬
        ordering = ['-price_updated_at']

    def __str__(self):
        return f'{self.book.title_korean} - {self.price} ({self.price_updated_at})'

class AuthorWork(models.Model):
    """
    저자와 책의 다대다 관계에 '곡 수' 정보를 추가하는 중간 모델
    """
    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name="author")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="book")
    number_of_songs = models.PositiveIntegerField(default=1, verbose_name="number_of_songs")

    class Meta:
        verbose_name = "AuthorWork"
        verbose_name_plural = "AuthorWork_list"
        # 한 저자가 한 책에 대해 여러 작업을 하지 않도록 유니크 제약조건 추가
        unique_together = ('author', 'book')

    def __str__(self):
        return f'{self.author.name} - {self.book.title_korean} ({self.number_of_songs}곡)'
    