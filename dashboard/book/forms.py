# book/forms.py

from django import forms
from .models import Book, Author, Category, Composer, ComposerWork, PriceHistory
from django.forms import inlineformset_factory
from django.utils import timezone

class BookForm(forms.ModelForm):
    # 1. 'category'는 ModelForm의 필드 목록에서 제외하고,
    #    사용자 입력을 받을 두 개의 '비어있는' ChoiceField를 수동으로 추가합니다.
    category1 = forms.ChoiceField(label="카테고리1", required=True)
    category2 = forms.ChoiceField(label="카테고리2", required=True)
    
    authors = forms.ModelMultipleChoiceField(
        queryset=Author.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        label="저자",
        required=False
    )
    current_price = forms.IntegerField(label="가격", min_value=0, required=True)

    class Meta:
        model = Book
        fields = [
            'title_korean', 'title_original', 'authors', 'publisher', 
            'current_price', 'book_type'
        ] # <-- 'category' 필드를 여기서 반드시 제거해야 합니다.
        widgets = {
            'publication_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. 카테고리1의 기본 텍스트를 '카테고리1'로 변경
        cat1_choices = [('', '카테고리1')] + [
            (cat1, cat1) for cat1 in Category.objects.values_list('category1', flat=True).distinct().order_by('category1')
        ]
        self.fields['category1'].choices = cat1_choices
        
        # 2. 카테고리2의 기본 텍스트를 '카테고리2'로 변경
        self.fields['category2'].choices = [('', '카테고리2')]
        
        # (수정 시)
        if self.instance and self.instance.pk and self.instance.category:
            cat1 = self.instance.category.category1
            cat2 = self.instance.category.category2
            
            self.fields['category1'].initial = cat1
            
            # 3. 여기도 '카테고리2'로 변경
            cat2_choices = [('', '카테고리2')] + [
                (c, c) for c in Category.objects.filter(category1=cat1).values_list('category2', flat=True).distinct().order_by('category2')
            ]
            self.fields['category2'].choices = cat2_choices
            self.fields['category2'].initial = cat2

    def clean(self):
        cleaned_data = super().clean()
        cat1 = cleaned_data.get('category1')
        cat2 = cleaned_data.get('category2')

        # 4. 사용자가 cat1과 cat2를 모두 선택했는지 확인합니다.
        if cat1 and cat2:
            try:
                # 5. 두 값의 조합으로 실제 Category 객체를 찾습니다.
                category_obj = Category.objects.get(category1=cat1, category2=cat2)
                # 6. 나중에 save() 메서드에서 사용할 수 있도록 cleaned_data에 저장합니다.
                cleaned_data['category'] = category_obj
            except Category.DoesNotExist:
                # 조합이 없는 경우 에러 발생
                self.add_error(None, "선택한 카테고리1과 카테고리2의 조합이 존재하지 않습니다. 카테고리를 확인해주세요.")
        elif not cat1:
             self.add_error('category1', "카테고리1을 선택해주세요.")
        elif not cat2:
             self.add_error('category2', "카테고리2를 선택해주세요.")

        return cleaned_data

    def save(self, commit=True):
        # 7. book 인스턴스를 생성 (category는 아직 저장 안 됨)
        book = super().save(commit=False)
        
        # 8. clean()에서 찾아둔 'category' 객체를 book 인스턴스에 직접 연결
        book.category = self.cleaned_data.get('category')
        
        # 9. 나머지 저장 로직(가격 등)을 실행
        if commit:
            book.save()
            self.save_m2m() # ManyToMany 필드(authors) 저장
            
            price = self.cleaned_data.get('current_price')
            if price is not None:
                PriceHistory.objects.create(
                    book=book,
                    price=price,
                    price_updated_at=timezone.now()
                )
        return book

class ComposerWorkForm(forms.ModelForm):
    # ChoiceField를 다시 CharField와 DateField로 변경합니다.
    composer_name = forms.CharField(label="작곡가명", widget=forms.TextInput(attrs={'placeholder': '작곡가명'}))
    date_of_birth = forms.DateField(label="생년월일", required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = ComposerWork
        # 필드 목록을 원래대로 복구합니다.
        fields = ['composer_name', 'date_of_birth', 'number_of_songs', 'royalty_percentage']
        widgets = {
            'number_of_songs': forms.NumberInput(attrs={'placeholder': '곡 수'}),
            'royalty_percentage': forms.NumberInput(attrs={'placeholder': '저작권료(%)'})
        }

# inlineformset_factory의 fields 목록도 수정합니다.
ComposerWorkFormSet = inlineformset_factory(
    Book, 
    ComposerWork, 
    form=ComposerWorkForm,
    # [핵심] fields 인자를 완전히 제거합니다. 
    # form=ComposerWorkForm을 지정했기 때문에 Django가 알아서 모든 필드를 가져옵니다.
    extra=1, 
    can_delete=True
)