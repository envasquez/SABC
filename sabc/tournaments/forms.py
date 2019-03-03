from django import forms

from .models import Tournament


class TournamentForm(forms.ModelForm):

    class Meta:
        model = Tournament
        fiels = '__all__'
        exclude = ['created_by', 'updated_by']