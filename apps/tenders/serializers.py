from rest_framework import serializers

from .models import Tender, TenderDocument


class TenderDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenderDocument
        fields = ["id", "title", "url"]


class TenderSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Tender
        fields = [
            "id", "source_code", "source_name", "external_id", "number",
            "title", "customer", "price", "region", "fz_type", "url",
            "published_at", "deadline_at", "documents",
            "first_seen_at", "updated_at",
        ]
