from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100, verbose_name='name')

    def __str__(self):
        return self.name

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
    author = models.ForeignKey(Author, on_delete=models.CASCADE, verbose_name='author_name')

    # 카테고리 ID (ForeignKey)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='category')

    title_korean = models.CharField(max_length=200, verbose_name='title_korean')
    title_original = models.CharField(max_length=200, verbose_name='title_original', null=True, blank=True)
    price = models.IntegerField(verbose_name='price')
    book_type = models.CharField(max_length=3, choices=BOOK_TYPES, default='GEN', verbose_name='book_type')
    price_updated_at = models.DateTimeField(auto_now=True, verbose_name='price_updated_at')
    subtitle = models.CharField(max_length=200, verbose_name='subtitle', null=True, blank=True)

    def __str__(self):
        return self.title_korean