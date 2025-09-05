from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'email', 'rating', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسمك'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'بريدك الإلكتروني'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'اكتب رأيك'}),
        }
