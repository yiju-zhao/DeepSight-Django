"""
Notebook-related serializers for the notebooks module following DRF best practices.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from ..models import Notebook

User = get_user_model()


class NotebookSerializer(serializers.ModelSerializer):
    """
    Serializer for Notebook model with comprehensive field handling.
    
    Provides basic CRUD operations with proper validation and read-only fields.
    Returns camelCase field names for frontend compatibility.
    """
    
    # Computed fields with camelCase names
    sourceCount = serializers.SerializerMethodField()
    itemCount = serializers.SerializerMethodField()
    chatMessageCount = serializers.SerializerMethodField()
    lastActivity = serializers.SerializerMethodField()
    ragflowDatasetInfo = serializers.SerializerMethodField()
    
    # Map snake_case model fields to camelCase
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    # Additional fields that might be useful
    isProcessing = serializers.SerializerMethodField()
    
    class Meta:
        model = Notebook
        fields = [
            "id", "name", "description", "createdAt", "updatedAt",
            "sourceCount", "itemCount", "chatMessageCount", 
            "lastActivity", "ragflowDatasetInfo", "isProcessing"
        ]
        read_only_fields = [
            "id", "createdAt", "updatedAt", "sourceCount", 
            "itemCount", "chatMessageCount", "lastActivity",
            "ragflowDatasetInfo", "isProcessing"
        ]
    
    def get_sourceCount(self, obj):
        """Get count of knowledge base items in the notebook."""
        return obj.knowledge_base_items.count()
    
    def get_itemCount(self, obj):
        """Get count of processed knowledge base items."""
        return obj.knowledge_base_items.filter(parsing_status='done').count()
    
    def get_chatMessageCount(self, obj):
        """Get count of chat messages in the notebook."""
        return obj.chat_messages.count()
    
    def get_lastActivity(self, obj):
        """Get the timestamp of the last activity in the notebook."""
        latest_kb_item = obj.knowledge_base_items.order_by('-updated_at').first()
        latest_chat = obj.chat_messages.order_by('-timestamp').first()
        
        last_activity = obj.updated_at
        
        if latest_kb_item and latest_kb_item.updated_at > last_activity:
            last_activity = latest_kb_item.updated_at
        
        if latest_chat and latest_chat.timestamp > last_activity:
            last_activity = latest_chat.timestamp
        
        return last_activity
    
    def get_ragflowDatasetInfo(self, obj):
        """Get RagFlow dataset information for the notebook."""
        try:
            ragflow_dataset = obj.ragflow_dataset
            return {
                "id": ragflow_dataset.ragflow_dataset_id,
                "status": ragflow_dataset.status,
                "isReady": ragflow_dataset.is_ready(),
                "documentCount": ragflow_dataset.get_document_count() if ragflow_dataset.is_ready() else 0,
                "errorMessage": ragflow_dataset.error_message or None
            }
        except AttributeError:
            # No RagFlow dataset exists yet
            return {
                "id": None,
                "status": "not_created",
                "isReady": False,
                "documentCount": 0,
                "errorMessage": None
            }
    
    def get_isProcessing(self, obj):
        """Check if the notebook has any processing items."""
        return obj.knowledge_base_items.filter(parsing_status__in=['pending', 'processing']).exists()
    
    def validate_name(self, value):
        """Validate notebook name."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")
        
        if len(value.strip()) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        return value.strip()
    
    def validate_description(self, value):
        """Validate notebook description."""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
        
        return value.strip() if value else ""


class NotebookListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for notebook listing with minimal fields.
    
    Used in list views where full detail is not needed for performance.
    Returns camelCase field names for frontend compatibility.
    """
    
    # CamelCase computed fields
    sourceCount = serializers.SerializerMethodField()
    itemCount = serializers.SerializerMethodField()
    isProcessing = serializers.SerializerMethodField()
    
    # Map snake_case model fields to camelCase
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    
    class Meta:
        model = Notebook
        fields = ["id", "name", "description", "createdAt", "updatedAt", "sourceCount", "itemCount", "isProcessing"]
        read_only_fields = ["id", "createdAt", "updatedAt", "sourceCount", "itemCount", "isProcessing"]
    
    def get_sourceCount(self, obj):
        """Get total count of sources in the notebook."""
        return obj.knowledge_base_items.count()
    
    def get_itemCount(self, obj):
        """Get count of processed items in the notebook."""
        return obj.knowledge_base_items.filter(parsing_status='done').count()
    
    def get_isProcessing(self, obj):
        """Check if the notebook has any processing items."""
        return obj.knowledge_base_items.filter(parsing_status__in=['pending', 'processing']).exists()


class NotebookCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for notebook creation with specific validation rules.
    """
    
    class Meta:
        model = Notebook
        fields = ["name", "description"]
    
    def validate_name(self, value):
        """Validate notebook name for creation."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name is required.")
        
        value = value.strip()
        
        if len(value) < 2:
            raise serializers.ValidationError("Notebook name must be at least 2 characters long.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        # Check for duplicate names for the user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            if Notebook.objects.filter(user=request.user, name__iexact=value).exists():
                raise serializers.ValidationError("A notebook with this name already exists.")
        
        return value
    
    def create(self, validated_data):
        """Create notebook with user from request context."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        
        return super().create(validated_data)


class NotebookUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for notebook updates with specific validation rules.
    """
    
    class Meta:
        model = Notebook
        fields = ["name", "description"]
    
    def validate_name(self, value):
        """Validate notebook name for updates."""
        if not value or not value.strip():
            raise serializers.ValidationError("Notebook name cannot be empty.")
        
        value = value.strip()
        
        if len(value) < 2:
            raise serializers.ValidationError("Notebook name must be at least 2 characters long.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Notebook name cannot exceed 100 characters.")
        
        # Check for duplicate names for the user (excluding current notebook)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and self.instance:
            if Notebook.objects.filter(
                user=request.user, 
                name__iexact=value
            ).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("A notebook with this name already exists.")
        
        return value 