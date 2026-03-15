"""
Form Builder for Browser Automation
Create, manage, and auto-fill forms
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """A single form field"""
    name: str
    selector: str
    field_type: str  # text, email, password, checkbox, select, textarea
    required: bool = False
    default_value: str = None
    autocomplete: str = None


@dataclass
class Form:
    """A form definition"""
    id: str
    name: str
    url_pattern: str  # URL pattern this form applies to
    fields: List[FormField] = field(default_factory=list)
    submit_button: str = None
    created_at: str = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'url_pattern': self.url_pattern,
            'fields': [
                {
                    'name': f.name,
                    'selector': f.selector,
                    'field_type': f.field_type,
                    'required': f.required,
                    'default_value': f.default_value,
                    'autocomplete': f.autocomplete
                }
                for f in self.fields
            ],
            'submit_button': self.submit_button,
            'created_at': self.created_at
        }


class FormBuilder:
    """
    Visual form builder and manager
    """
    
    FORMS_FILE = "forms.json"
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.forms: Dict[str, Form] = {}
        self._load_forms()
    
    def _load_forms(self):
        """Load forms from storage"""
        if not self.storage_path:
            return
        
        try:
            forms_file = f"{self.storage_path}/{self.FORMS_FILE}"
            with open(forms_file, 'r') as f:
                data = json.load(f)
            
            for form_data in data.get('forms', []):
                fields = [
                    FormField(
                        name=f['name'],
                        selector=f['selector'],
                        field_type=f.get('field_type', 'text'),
                        required=f.get('required', False),
                        default_value=f.get('default_value'),
                        autocomplete=f.get('autocomplete')
                    )
                    for f in form_data.get('fields', [])
                ]
                
                self.forms[form_data['id']] = Form(
                    id=form_data['id'],
                    name=form_data['name'],
                    url_pattern=form_data['url_pattern'],
                    fields=fields,
                    submit_button=form_data.get('submit_button'),
                    created_at=form_data.get('created_at')
                )
                
        except FileNotFoundError:
            logger.info("No forms file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading forms: {e}")
    
    def _save_forms(self):
        """Save forms to storage"""
        if not self.storage_path:
            return
        
        try:
            forms_file = f"{self.storage_path}/{self.FORMS_FILE}"
            data = {
                'forms': [form.to_dict() for form in self.forms.values()]
            }
            
            with open(forms_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving forms: {e}")
    
    def create_form(self, name: str, url_pattern: str) -> Form:
        """Create a new form"""
        form_id = f"form_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        form = Form(
            id=form_id,
            name=name,
            url_pattern=url_pattern,
            created_at=datetime.now().isoformat()
        )
        
        self.forms[form_id] = form
        self._save_forms()
        
        logger.info(f"Created form: {name}")
        return form
    
    def add_field(
        self,
        form_id: str,
        name: str,
        selector: str,
        field_type: str = "text",
        required: bool = False,
        default_value: str = None
    ) -> bool:
        """Add a field to a form"""
        if form_id not in self.forms:
            logger.error(f"Form not found: {form_id}")
            return False
        
        field = FormField(
            name=name,
            selector=selector,
            field_type=field_type,
            required=required,
            default_value=default_value
        )
        
        self.forms[form_id].fields.append(field)
        self._save_forms()
        
        logger.info(f"Added field to form {form_id}: {name}")
        return True
    
    def set_submit_button(self, form_id: str, selector: str):
        """Set the submit button selector"""
        if form_id not in self.forms:
            return False
        
        self.forms[form_id].submit_button = selector
        self._save_forms()
        return True
    
    def get_form(self, form_id: str) -> Optional[Form]:
        """Get a form by ID"""
        return self.forms.get(form_id)
    
    def find_form_by_url(self, url: str) -> Optional[Form]:
        """Find a form that matches the URL"""
        for form in self.forms.values():
            if form.url_pattern in url:
                return form
        return None
    
    def list_forms(self) -> List[Form]:
        """List all forms"""
        return list(self.forms.values())
    
    def delete_form(self, form_id: str) -> bool:
        """Delete a form"""
        if form_id not in self.forms:
            return False
        
        del self.forms[form_id]
        self._save_forms()
        return True
    
    def fill_form_data(self, form_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare form fill data with memory integration
        Uses memory to auto-fill fields
        """
        form = self.get_form(form_id)
        if not form:
            return {}
        
        fill_data = {}
        
        for field in form.fields:
            # Use provided data first
            if field.name in data:
                fill_data[field.selector] = data[field.name]
            # Use default value
            elif field.default_value:
                fill_data[field.selector] = field.default_value
            # TODO: Could integrate with memory here for auto-fill
        
        return fill_data
    
    def export_form(self, form_id: str) -> str:
        """Export form as JSON string"""
        form = self.get_form(form_id)
        if not form:
            return ""
        
        return json.dumps(form.to_dict(), indent=2)
    
    def import_form(self, json_str: str) -> bool:
        """Import form from JSON"""
        try:
            data = json.loads(json_str)
            
            form = Form(
                id=data['id'],
                name=data['name'],
                url_pattern=data['url_pattern'],
                fields=[
                    FormField(
                        name=f['name'],
                        selector=f['selector'],
                        field_type=f.get('field_type', 'text'),
                        required=f.get('required', False),
                        default_value=f.get('default_value'),
                        autocomplete=f.get('autocomplete')
                    )
                    for f in data.get('fields', [])
                ],
                submit_button=data.get('submit_button'),
                created_at=data.get('created_at')
            )
            
            self.forms[form.id] = form
            self._save_forms()
            return True
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False


def create_form_builder(storage_path: str = None) -> FormBuilder:
    """Factory function"""
    return FormBuilder(storage_path)
