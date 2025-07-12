# facility_landing/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from .models import FacilityLandingPage, FacilityGallery, FacilityTestimonial


class FacilityLandingPageForm(forms.ModelForm):
    """Form for editing facility landing page content"""
    
    class Meta:
        model = FacilityLandingPage
        fields = [
            'hero_image',
            'hero_tagline',
            'hero_description',
            'mission_statement',
            'facility_story',
            'years_of_experience',
            'services_description',
            'specialized_care',
            'accreditations',
            'amenities',
            'staff_credentials',
            'visiting_hours',
            'tour_available',
            'meta_title',
            'meta_description',
            'is_published',
        ]
        
        widgets = {
            'hero_tagline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a compelling tagline for your facility',
                'maxlength': 200
            }),
            'hero_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description shown in the hero section',
                'maxlength': 500
            }),
            'mission_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your facility\'s mission and philosophy of care'
            }),
            'facility_story': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share the history and background of your facility'
            }),
            'years_of_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Number of years in operation',
                'min': 0,
                'max': 100
            }),
            'services_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Detailed description of services and care provided'
            }),
            'specialized_care': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Specialized care programs and treatments offered'
            }),
            'accreditations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'List accreditations, certifications, and awards'
            }),
            'amenities': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'List facility amenities and features'
            }),
            'staff_credentials': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Information about staff qualifications and training'
            }),
            'visiting_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Daily 9:00 AM - 8:00 PM',
                'maxlength': 200
            }),
            'tour_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Custom page title for SEO (max 60 characters)',
                'maxlength': 60
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Custom meta description for SEO (max 160 characters)',
                'maxlength': 160
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'hero_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        
        labels = {
            'hero_image': 'Hero Image',
            'hero_tagline': 'Hero Tagline',
            'hero_description': 'Hero Description',
            'mission_statement': 'Mission Statement',
            'facility_story': 'Facility History & Story',
            'years_of_experience': 'Years of Experience',
            'services_description': 'Services & Care Description',
            'specialized_care': 'Specialized Care Programs',
            'accreditations': 'Accreditations & Certifications',
            'amenities': 'Amenities & Features',
            'staff_credentials': 'Staff Credentials',
            'visiting_hours': 'Visiting Hours',
            'tour_available': 'Tours Available',
            'meta_title': 'SEO Page Title',
            'meta_description': 'SEO Meta Description',
            'is_published': 'Publish Landing Page',
        }
        
        help_texts = {
            'hero_image': 'Upload a high-quality image for the hero section (recommended: 1920x1080px, max 5MB)',
            'hero_tagline': 'A compelling headline that captures your facility\'s essence',
            'hero_description': 'Brief description that appears prominently on your landing page',
            'mission_statement': 'Your facility\'s mission and philosophy of care',
            'facility_story': 'Share your facility\'s history, background, and what makes you unique',
            'years_of_experience': 'How many years your facility has been in operation',
            'services_description': 'Detailed description of all services and care you provide',
            'specialized_care': 'Any specialized programs, treatments, or care you offer',
            'accreditations': 'List all certifications, accreditations, awards, and recognitions',
            'amenities': 'Facility amenities, features, and what makes your facility special',
            'staff_credentials': 'Information about your staff\'s qualifications and training',
            'visiting_hours': 'When families and friends can visit residents',
            'tour_available': 'Check if you offer facility tours to prospective residents and families',
            'meta_title': 'Custom page title that appears in search engines (max 60 characters)',
            'meta_description': 'Description that appears in search engine results (max 160 characters)',
            'is_published': 'Uncheck to hide your landing page from public view',
        }
    
    def clean_hero_image(self):
        """Validate hero image"""
        image = self.cleaned_data.get('hero_image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large. Please upload an image smaller than 5MB.")
            
            # Check image dimensions (optional)
            try:
                from PIL import Image
                img = Image.open(image)
                width, height = img.size
                if width < 800 or height < 400:
                    raise ValidationError("Image too small. Please upload an image at least 800x400 pixels.")
                
                # Check aspect ratio (optional - for better hero display)
                aspect_ratio = width / height
                if aspect_ratio < 1.5 or aspect_ratio > 3.0:
                    raise ValidationError("For best results, use an image with an aspect ratio between 1.5:1 and 3:1 (e.g., 1920x1080).")
                    
            except ImportError:
                # PIL not available, skip dimension check
                pass
            except Exception:
                # If we can't check dimensions, that's okay
                pass
        
        return image
    
    def clean_meta_title(self):
        """Validate meta title length"""
        meta_title = self.cleaned_data.get('meta_title')
        if meta_title and len(meta_title) > 60:
            raise ValidationError("Meta title must be 60 characters or less for optimal SEO.")
        return meta_title
    
    def clean_meta_description(self):
        """Validate meta description length"""
        meta_description = self.cleaned_data.get('meta_description')
        if meta_description and len(meta_description) > 160:
            raise ValidationError("Meta description must be 160 characters or less for optimal SEO.")
        return meta_description
    
    def clean_years_of_experience(self):
        """Validate years of experience"""
        years = self.cleaned_data.get('years_of_experience')
        if years is not None:
            if years < 0:
                raise ValidationError("Years of experience cannot be negative.")
            if years > 100:
                raise ValidationError("Years of experience seems too high. Please verify the number.")
        return years
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        # Ensure at least some content is provided for published pages
        is_published = cleaned_data.get('is_published')
        hero_tagline = cleaned_data.get('hero_tagline')
        hero_description = cleaned_data.get('hero_description')
        
        if is_published and not (hero_tagline and hero_description):
            raise ValidationError("Hero tagline and description are required for published landing pages.")
        
        return cleaned_data


class FacilityGalleryForm(forms.ModelForm):
    """Form for uploading gallery images"""
    
    class Meta:
        model = FacilityGallery
        fields = ['image', 'title', 'description', 'category', 'is_featured']
        
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter image title/caption',
                'maxlength': 100
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Detailed description of the image (optional)'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'image': 'Upload Image',
            'title': 'Image Title',
            'description': 'Image Description',
            'category': 'Image Category',
            'is_featured': 'Featured Image',
        }
        
        help_texts = {
            'image': 'Upload a high-quality image (recommended: 800x600px or higher, max 5MB)',
            'title': 'A descriptive title for this image',
            'description': 'Optional detailed description of what the image shows',
            'category': 'Choose the most appropriate category for organizing your gallery',
            'is_featured': 'Featured images are displayed more prominently',
        }
    
    def clean_image(self):
        """Validate gallery image"""
        image = self.cleaned_data.get('image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image file too large. Please upload an image smaller than 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise ValidationError("Please upload a valid image file (JPEG, PNG, or WebP).")
            
            # Check image dimensions
            try:
                width, height = get_image_dimensions(image)
                if width and height:
                    if width < 400 or height < 300:
                        raise ValidationError("Image too small. Please upload an image at least 400x300 pixels.")
                    if width > 4000 or height > 4000:
                        raise ValidationError("Image too large. Please upload an image smaller than 4000x4000 pixels.")
            except Exception:
                # If we can't check dimensions, that's okay
                pass
        
        return image
    
    def clean_title(self):
        """Validate image title"""
        title = self.cleaned_data.get('title')
        if title:
            # Remove extra whitespace
            title = ' '.join(title.split())
            if len(title) < 3:
                raise ValidationError("Image title should be at least 3 characters long.")
        return title


class TestimonialForm(forms.ModelForm):
    """Form for adding testimonials"""
    
    class Meta:
        model = FacilityTestimonial
        fields = ['author_name', 'author_relation', 'testimonial_text', 'rating', 'is_featured']
        
        widgets = {
            'author_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter the name of the person giving this testimonial',
                'maxlength': 100
            }),
            'author_relation': forms.Select(attrs={
                'class': 'form-select'
            }),
            'testimonial_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Enter the testimonial content...'
            }),
            'rating': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'author_name': 'Author Name',
            'author_relation': 'Relationship to Facility',
            'testimonial_text': 'Testimonial',
            'rating': 'Star Rating',
            'is_featured': 'Featured Testimonial',
        }
        
        help_texts = {
            'author_name': 'The name of the person giving this testimonial',
            'author_relation': 'How this person is connected to your facility',
            'testimonial_text': 'The full testimonial text',
            'rating': 'Optional star rating (1-5 stars)',
            'is_featured': 'Featured testimonials are displayed more prominently',
        }
    
    def clean_testimonial_text(self):
        """Validate testimonial length"""
        text = self.cleaned_data.get('testimonial_text')
        if text:
            # Clean up whitespace
            text = ' '.join(text.split())
            if len(text) < 10:
                raise ValidationError("Testimonial is too short. Please provide at least 10 characters.")
            if len(text) > 1000:
                raise ValidationError("Testimonial is too long. Please keep it under 1000 characters.")
        return text
    
    def clean_author_name(self):
        """Validate author name"""
        name = self.cleaned_data.get('author_name')
        if name:
            # Clean up whitespace
            name = ' '.join(name.split())
            if len(name) < 2:
                raise ValidationError("Author name should be at least 2 characters long.")
            # Check for valid characters (letters, spaces, common punctuation)
            import re
            if not re.match(r'^[a-zA-Z\s\.\-\']+$', name):
                raise ValidationError("Author name contains invalid characters. Please use only letters, spaces, periods, hyphens, and apostrophes.")
        return name


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads"""
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        attrs.update({'multiple': True})
        self.attrs = attrs

    def value_from_datadict(self, data, files, name):
        upload = files.getlist(name)
        if not upload:
            return None
        return upload


class MultipleFileField(forms.FileField):
    """Custom field for handling multiple file uploads"""
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BulkGalleryUploadForm(forms.Form):
    """Form for uploading multiple gallery images at once"""
    
    images = MultipleFileField(
        help_text='Select multiple images to upload at once (max 10 images, 5MB each)',
        label='Upload Images'
    )
    
    category = forms.ChoiceField(
        choices=FacilityGallery._meta.get_field('category').choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='All uploaded images will be assigned to this category',
        label='Image Category'
    )
    
    default_title_prefix = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., "Room", "Common Area"'
        }),
        help_text='Optional prefix for image titles (will be numbered automatically)',
        label='Title Prefix'
    )
    
    def clean_images(self):
        """Validate multiple images"""
        images = self.cleaned_data.get('images')
        if not images:
            raise ValidationError("Please select at least one image to upload.")
        
        if not isinstance(images, list):
            images = [images]
        
        if len(images) > 10:
            raise ValidationError("You can upload a maximum of 10 images at once.")
        
        total_size = 0
        for image in images:
            # Check individual file size
            if image.size > 5 * 1024 * 1024:
                raise ValidationError(f"Image '{image.name}' is too large. Please upload images smaller than 5MB.")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise ValidationError(f"'{image.name}' is not a valid image file. Please upload JPEG, PNG, or WebP files.")
            
            total_size += image.size
        
        # Check total size (max 50MB for all images combined)
        if total_size > 50 * 1024 * 1024:
            raise ValidationError("Total file size too large. Please upload fewer or smaller images.")
        
        return images


class LandingPageSettingsForm(forms.ModelForm):
    """Form for landing page settings and preferences"""
    
    class Meta:
        model = FacilityLandingPage
        fields = ['is_published', 'meta_title', 'meta_description']
        
        widgets = {
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 60,
                'placeholder': 'Custom page title for search engines'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 160,
                'placeholder': 'Brief description for search engine results'
            }),
        }
        
        labels = {
            'is_published': 'Publish Landing Page',
            'meta_title': 'SEO Page Title',
            'meta_description': 'SEO Meta Description',
        }
        
        help_texts = {
            'is_published': 'Uncheck to hide your landing page from public view',
            'meta_title': 'Custom page title that appears in search engines (max 60 characters)',
            'meta_description': 'Description that appears in search engine results (max 160 characters)',
        }


class QuickEditForm(forms.ModelForm):
    """Simplified form for quick edits to landing page"""
    
    class Meta:
        model = FacilityLandingPage
        fields = ['hero_tagline', 'hero_description', 'is_published']
        
        widgets = {
            'hero_tagline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a compelling tagline',
                'maxlength': 200
            }),
            'hero_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Brief description for your hero section',
                'maxlength': 500
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ContactForm(forms.Form):
    """Contact form for facility inquiries from landing page"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Full Name',
            'required': True
        }),
        label='Full Name'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com',
            'required': True
        }),
        label='Email Address'
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(555) 123-4567',
            'type': 'tel'
        }),
        label='Phone Number'
    )
    
    inquiry_type = forms.ChoiceField(
        choices=[
            ('general', 'General Information'),
            ('tour', 'Schedule a Tour'),
            ('admission', 'Admission Inquiry'),
            ('pricing', 'Pricing Information'),
            ('availability', 'Bed Availability'),
            ('other', 'Other'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Type of Inquiry'
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please tell us about your needs or questions...',
            'required': True
        }),
        label='Message'
    )
    
    preferred_contact_method = forms.ChoiceField(
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('either', 'Either Email or Phone'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Preferred Contact Method'
    )
    
    def clean_phone(self):
        """Validate phone number format"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove non-numeric characters
            import re
            phone_digits = re.sub(r'[^\d]', '', phone)
            if len(phone_digits) < 10:
                raise ValidationError("Please enter a valid phone number with at least 10 digits.")
            if len(phone_digits) > 15:
                raise ValidationError("Phone number is too long. Please check the number.")
        return phone
    
    def clean_message(self):
        """Validate message content"""
        message = self.cleaned_data.get('message')
        if message:
            if len(message.strip()) < 10:
                raise ValidationError("Please provide a more detailed message (at least 10 characters).")
        return message