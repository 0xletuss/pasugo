"""
Cloudinary Media Management
Handles all file uploads to Cloudinary with proper error handling
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from fastapi import UploadFile, HTTPException, status
from config import settings
import logging
import io
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)


class CloudinaryManager:
    """Manager for all Cloudinary operations"""
    
    @staticmethod
    async def upload_file(
        file: UploadFile,
        folder: str,
        public_id: Optional[str] = None,
        resource_type: str = "auto"
    ) -> dict:
        """
        Upload file to Cloudinary
        
        Args:
            file: FastAPI UploadFile object
            folder: Cloudinary folder path (e.g., "pasugo/riders", "pasugo/bills")
            public_id: Optional custom public ID for the file
            resource_type: Type of resource - "auto", "image", "video", "raw"
            
        Returns:
            Dict with upload details including secure_url
            
        Raises:
            HTTPException if upload fails
        """
        try:
            # Validate file size
            contents = await file.read()
            if len(contents) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / (1024*1024)}MB"
                )
            
            # Validate file type
            allowed_types = {
                "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
                "video": ["video/mp4", "video/mpeg"],
                "document": ["application/pdf", "application/msword"]
            }
            
            # Reset file pointer after reading
            await file.seek(0)
            
            # Determine resource type and validate
            if file.content_type and file.content_type.startswith("image/"):
                resource_type = "image"
            elif file.content_type and file.content_type.startswith("video/"):
                resource_type = "video"
            else:
                resource_type = "auto"
            
            # Upload to Cloudinary
            full_folder = f"{settings.CLOUDINARY_FOLDER_PREFIX}/{folder}"
            
            response = cloudinary.uploader.upload(
                contents,
                folder=full_folder,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
                invalidate=True
            )
            
            logger.info(f"File uploaded successfully: {response.get('public_id')}")
            
            return {
                "success": True,
                "public_id": response.get("public_id"),
                "url": response.get("secure_url"),
                "resource_type": response.get("resource_type"),
                "format": response.get("format"),
                "size": response.get("bytes"),
                "width": response.get("width"),
                "height": response.get("height")
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cloudinary upload error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
    
    @staticmethod
    def delete_file(public_id: str, resource_type: str = "image") -> bool:
        """
        Delete file from Cloudinary
        
        Args:
            public_id: Public ID of file to delete
            resource_type: Type of resource to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            if result.get("result") == "ok":
                logger.info(f"File deleted successfully: {public_id}")
                return True
            else:
                logger.warning(f"File deletion returned unexpected result: {result}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {public_id}: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def get_file_url(public_id: str, transformations: Optional[dict] = None) -> str:
        """
        Get secure URL for a file, with optional transformations
        
        Args:
            public_id: Public ID of the file
            transformations: Optional dict of transformations (resize, etc.)
            
        Returns:
            Secure URL of the file
        """
        try:
            # Build transformation options
            options = {
                "secure": True
            }
            
            if transformations:
                # Example transformations:
                # {"width": 300, "height": 300, "crop": "fill"}
                options.update(transformations)
            
            url = cloudinary.CloudinaryResource(public_id).build_url(**options)
            return url
        except Exception as e:
            logger.error(f"Error generating URL for {public_id}: {str(e)}")
            return None
    
    @staticmethod
    def generate_thumbnail(public_id: str, width: int = 200, height: int = 200) -> str:
        """
        Generate thumbnail URL for an image
        
        Args:
            public_id: Public ID of the image
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Secure URL of the thumbnail
        """
        try:
            url = cloudinary.CloudinaryResource(public_id).build_url(
                secure=True,
                width=width,
                height=height,
                crop="fill",
                gravity="auto"
            )
            return url
        except Exception as e:
            logger.error(f"Error generating thumbnail for {public_id}: {str(e)}")
            return None
    
    @staticmethod
    def get_upload_url(folder: str) -> dict:
        """
        Generate a signed URL and additional parameters for client-side uploads
        Useful for frontend direct uploads without sending files through backend
        
        Args:
            folder: Cloudinary folder path
            
        Returns:
            Dict with upload parameters
        """
        try:
            from datetime import datetime, timedelta
            
            timestamp = int(datetime.now().timestamp())
            
            params = {
                "timestamp": timestamp,
                "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
                "api_key": settings.CLOUDINARY_API_KEY,
                "folder": f"{settings.CLOUDINARY_FOLDER_PREFIX}/{folder}",
                "resource_type": "auto",
                "secure": True
            }
            
            # Generate signature
            from cloudinary.utils import cloudinary_api_sign_request
            signature = cloudinary.utils.build_upload_params(params)
            
            return {
                "upload_url": f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/auto/upload",
                "params": params
            }
        except Exception as e:
            logger.error(f"Error generating upload URL: {str(e)}")
            return None
    
    @staticmethod
    def extract_public_id(url: str) -> Optional[str]:
        """
        Extract public_id from a Cloudinary URL
        
        Args:
            url: Cloudinary URL
            
        Returns:
            Public ID or None if not a Cloudinary URL
        """
        try:
            # Example URL: https://res.cloudinary.com/drw82hgul/image/upload/v1234567890/pasugo/riders/file.jpg
            if "cloudinary.com" not in url:
                return None
            
            # Extract public_id from URL
            parts = url.split("/upload/")
            if len(parts) < 2:
                return None
            
            # Get path after /upload/
            path = parts[1]
            # Remove file extension and version info
            public_id = "/".join(path.split("/")[1:]).rsplit(".", 1)[0]
            
            return public_id
        except Exception as e:
            logger.error(f"Error extracting public_id from URL: {str(e)}")
            return None
    
    @staticmethod
    def health_check() -> bool:
        """
        Check if Cloudinary is properly configured and accessible
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = cloudinary.api.ping()
            if result.get("status") == "ok":
                logger.info("Cloudinary connection successful")
                return True
            else:
                logger.error(f"Cloudinary health check failed: {result}")
                return False
        except Exception as e:
            logger.error(f"Cloudinary connection error: {str(e)}")
            return False


# Convenience functions

async def upload_rider_id_document(file: UploadFile, rider_id: int) -> str:
    """Upload rider ID document"""
    result = await CloudinaryManager.upload_file(
        file,
        folder="riders/id_documents",
        public_id=f"rider_{rider_id}",
        resource_type="auto"
    )
    return result["url"]


async def upload_bill_photo(file: UploadFile, request_id: int) -> str:
    """Upload bill photo"""
    result = await CloudinaryManager.upload_file(
        file,
        folder="bills/photos",
        public_id=f"bill_{request_id}",
        resource_type="image"
    )
    return result["url"]


async def upload_profile_photo(file: UploadFile, user_id: int) -> str:
    """Upload user profile photo"""
    result = await CloudinaryManager.upload_file(
        file,
        folder="users/profile_photos",
        public_id=f"user_{user_id}",
        resource_type="image"
    )
    return result["url"]


async def upload_complaint_attachment(file: UploadFile, complaint_id: int) -> str:
    """Upload complaint attachment"""
    result = await CloudinaryManager.upload_file(
        file,
        folder="complaints/attachments",
        public_id=f"complaint_{complaint_id}",
        resource_type="auto"
    )
    return result["url"]
