from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'email', 'rating', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rate from 1 to 5',
                'min': 1,
                'max': 5,
                'lang': 'en',
                'inputmode': 'numeric'
            }),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Text your Review'}),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['rating'].localize = False
            self.fields['rating'].initial = 5  # يخليها 5 إنجليزي مش ٥


