from django import forms
from django.core.exceptions import ValidationError
from pathlib import Path


class ProjectUploadForm(forms.Form):
    title = forms.CharField(max_length=255)
    file = forms.FileField()

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        extension = Path(uploaded.name).suffix.lower()
        if extension not in (".mp4", ".mov"):
            raise ValidationError("Only MP4 or MOV files are supported.")
        return uploaded


class ProcessingJobForm(forms.Form):
    DURATION_CHOICES = [(5, "5 min"), (7, "7 min"), (10, "10 min")]
    target_duration_minutes = forms.ChoiceField(choices=DURATION_CHOICES)
