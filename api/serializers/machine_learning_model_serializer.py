from rest_framework import serializers
from api.models.machine_learning_model import MachineLearningModel
import hashlib


class MachineLearningModelSerializer(serializers.ModelSerializer):
    model_file = serializers.FileField()
    scaler_file = serializers.FileField()

    class Meta:
        model = MachineLearningModel
        fields = [
            "id",
            "reservoir",
            "parameter",
            "model_file",
            "scaler_file",
            "model_file_hash",
            "scaler_file_hash",
            "created_at",
        ]
        read_only_fields = ["model_file_hash", "scaler_file_hash"]

    def compute_file_hash(self, file):
        sha256_hash = hashlib.sha256()
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
        file.seek(0)
        return sha256_hash.hexdigest()

    def validate(self, data):
        model_file = data.get("model_file")
        scaler_file = data.get("scaler_file")

        if model_file:
            model_file_hash = self.compute_file_hash(model_file)
            if MachineLearningModel.objects.filter(
                model_file_hash=model_file_hash
            ).exists():
                raise serializers.ValidationError(
                    "This model file has already been uploaded."
                )
            data["model_file_hash"] = model_file_hash
            data["model_file"] = model_file.read()

        if scaler_file:
            scaler_file_hash = self.compute_file_hash(scaler_file)
            if MachineLearningModel.objects.filter(
                scaler_file_hash=scaler_file_hash
            ).exists():
                raise serializers.ValidationError(
                    "This scaler file has already been uploaded."
                )
            data["scaler_file_hash"] = scaler_file_hash
            data["scaler_file"] = scaler_file.read()

        return data
