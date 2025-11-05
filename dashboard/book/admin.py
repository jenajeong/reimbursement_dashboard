from django.contrib import admin
from .models import Book, Author, PriceHistory, Composer, ComposerWork

admin.site.register(Book)
admin.site.register(Author)
admin.site.register(PriceHistory)
admin.site.register(Composer)
admin.site.register(ComposerWork)