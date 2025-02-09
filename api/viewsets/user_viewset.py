from rest_framework.permissions import IsAuthenticated, AllowAny
from api.models.user import User
from api.serializers.user_serializer import UserSerializer
from rest_framework import viewsets
from rest_framework import generics, mixins, views, viewsets


class UserViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    
# class UserViewSet(mixins.CreateModelMixin,
#                    mixins.RetrieveModelMixin,
#                    mixins.UpdateModelMixin,
#                    mixins.DestroyModelMixin,
#                    mixins.ListModelMixin,
#                    viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == "create":
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
