from rest_framework import viewsets, permissions
from .models import Materia
from .serializers import MateriaSerializer

class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer
    permission_classes = [permissions.IsAuthenticated]
