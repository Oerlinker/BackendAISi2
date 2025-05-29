from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User
from apps.cursos.serializers import CursoSerializer


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        return token


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    curso_detail = CursoSerializer(source='curso', read_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'curso', 'curso_detail', 'password',
                  'password2']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
            'curso': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})

        if 'curso' in attrs and attrs.get('curso') and attrs.get('role') != 'ESTUDIANTE':
            raise serializers.ValidationError({"curso": "Solo los estudiantes pueden ser asignados a un curso"})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data['role'],
            curso=validated_data.get('curso')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    curso_detail = CursoSerializer(source='curso', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'curso', 'curso_detail']
        read_only_fields = ['id', 'username', 'email', 'role', 'curso', 'curso_detail']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializador especial para que los administradores puedan actualizar usuarios.
    Permite modificar más campos que el serializador normal, incluyendo role y curso.
    """
    curso_detail = CursoSerializer(source='curso', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'curso', 'curso_detail']
        read_only_fields = ['id']
        
    def validate(self, attrs):
        # Si se está asignando un curso, verificar que el usuario sea estudiante
        if 'curso' in attrs and attrs.get('curso') and attrs.get('role', self.instance.role) != 'ESTUDIANTE':
            raise serializers.ValidationError({"curso": "Solo los estudiantes pueden ser asignados a un curso"})
        return attrs
