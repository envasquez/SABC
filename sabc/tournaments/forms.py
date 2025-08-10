# -*- coding: utf-8 -*-

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import FileField, Form, ModelForm, ValidationError

from .models.results import Result, TeamResult
from .models.tournaments import Events, Tournament


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = "__all__"
        exclude = ("created_by", "updated_by", "paper")


class EventForm(ModelForm):
    class Meta:
        model = Events
        fields = "__all__"
        exclude = ("type", "month")


class ResultForm(ModelForm):
    class Meta:
        model = Result
        fields = (
            "tournament",
            "angler",
            "buy_in",
            "locked",
            "dq_points",
            "disqualified",
            "num_fish",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )

    def __init__(self, *args, **kwargs):
        angler = kwargs.pop("angler")
        super().__init__(*args, **kwargs)
        self.fields["angler"].queryset = angler

        # Add validation ranges
        self.fields["num_fish"].validators = [
            MinValueValidator(0),
            MaxValueValidator(10),
        ]
        self.fields["num_fish_dead"].validators = [
            MinValueValidator(0),
            MaxValueValidator(10),
        ]
        self.fields["total_weight"].validators = [
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("50.00")),
        ]
        self.fields["big_bass_weight"].validators = [
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("15.00")),
        ]

    def clean(self):
        cleaned_data = super().clean()
        num_fish = cleaned_data.get("num_fish", 0)
        num_fish_dead = cleaned_data.get("num_fish_dead", 0)
        big_bass_weight = cleaned_data.get("big_bass_weight", Decimal("0.00"))
        total_weight = cleaned_data.get("total_weight", Decimal("0.00"))

        # Validate dead fish count
        if num_fish_dead > num_fish:
            raise ValidationError(
                "Number of dead fish cannot exceed total number of fish"
            )

        # Validate big bass weight
        if big_bass_weight > total_weight and total_weight > 0:
            raise ValidationError("Big bass weight cannot exceed total weight")

        return cleaned_data


class ResultUpdateForm(ModelForm):
    class Meta:
        model = Result
        fields = (
            "tournament",
            "angler",
            "buy_in",
            "locked",
            "dq_points",
            "disqualified",
            "place_finish",
            "points",
            "num_fish",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add validation ranges
        self.fields["num_fish"].validators = [
            MinValueValidator(0),
            MaxValueValidator(10),
        ]
        self.fields["num_fish_dead"].validators = [
            MinValueValidator(0),
            MaxValueValidator(10),
        ]
        self.fields["total_weight"].validators = [
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("50.00")),
        ]
        self.fields["big_bass_weight"].validators = [
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("15.00")),
        ]
        self.fields["place_finish"].validators = [
            MinValueValidator(1),
            MaxValueValidator(200),
        ]
        self.fields["points"].validators = [
            MinValueValidator(0),
            MaxValueValidator(200),
        ]

    def clean(self):
        cleaned_data = super().clean()
        num_fish = cleaned_data.get("num_fish", 0)
        num_fish_dead = cleaned_data.get("num_fish_dead", 0)
        big_bass_weight = cleaned_data.get("big_bass_weight", Decimal("0.00"))
        total_weight = cleaned_data.get("total_weight", Decimal("0.00"))

        # Validate dead fish count
        if num_fish_dead > num_fish:
            raise ValidationError(
                "Number of dead fish cannot exceed total number of fish"
            )

        # Validate big bass weight
        if big_bass_weight > total_weight and total_weight > 0:
            raise ValidationError("Big bass weight cannot exceed total weight")

        return cleaned_data


class TeamForm(ModelForm):
    class Meta:
        model = TeamResult
        fields = ("tournament", "result_1", "result_2")

    def __init__(self, *args, **kwargs):
        result_1 = kwargs.pop("result_1")
        result_2 = kwargs.pop("result_2")

        super().__init__(*args, **kwargs)
        self.fields["result_1"].queryset = result_1
        self.fields["result_2"].queryset = result_2


class YamlImportForm(Form):
    yaml_upload = FileField(help_text="Upload a YAML file (max 2MB)")

    def clean_yaml_upload(self):
        file = self.cleaned_data.get("yaml_upload")
        if file:
            # Check file size (2MB max)
            if file.size > 2 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 2MB")

            # Check file extension
            allowed_extensions = [".yaml", ".yml"]
            if not any(file.name.lower().endswith(ext) for ext in allowed_extensions):
                raise ValidationError("Only YAML files (.yaml, .yml) are allowed")

            # Check MIME type
            allowed_types = ["text/yaml", "application/x-yaml", "text/plain"]
            if hasattr(file, "content_type") and file.content_type not in allowed_types:
                raise ValidationError("Invalid file type. Please upload a YAML file")

        return file
