from django.contrib import admin
from .models import Book, Author, Category, PriceHistory, AuthorWork

admin.site.register(Book)
admin.site.register(Author)
admin.site.register(AuthorWork)
admin.site.register(Category)
admin.site.register(PriceHistory)
