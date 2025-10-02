import React, { useState, useEffect } from 'react';
import { Loader2, FileText } from 'lucide-react';
import { config } from "@/config";

const API_BASE_URL = config.API_BASE_URL;

interface AuthenticatedImageProps {
  src: string;
  alt?: string;
  title?: string;
  file?: any;
}

// Enhanced Authenticated Image component that handles both MinIO URLs and API URLs
const AuthenticatedImage: React.FC<AuthenticatedImageProps> = ({ src, alt, title, file }) => {
  const [imgSrc, setImgSrc] = useState(src);
  const [imgError, setImgError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    console.log('AuthenticatedImage: Processing image with src:', src, 'file:', file);
    setImgError(false);
    setIsLoading(true);

    // If the src is a blob URL or already a data URL, use it directly
    if (src.startsWith('blob:') || src.startsWith('data:')) {
      console.log('AuthenticatedImage: Using blob/data URL directly');
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // Check if this is a relative report image path (images/...)
    if (src.startsWith('images/')) {
      console.log('AuthenticatedImage: Detected relative report image path, file:', file);
      const imageName = src.replace('images/', '');

      if (!file) {
        console.error('AuthenticatedImage: No file object provided for relative image path');
        setImgError(true);
        setIsLoading(false);
        return;
      }

      // Check if this is a report file
      const reportId = file.report_id || file.id;
      console.log('AuthenticatedImage: File type:', file.type, 'Report ID:', reportId);

      if (file.type === 'report' && reportId) {
        const reportImageUrl = `${API_BASE_URL}/reports/${reportId}/images/${imageName}`;
        console.log('AuthenticatedImage: Constructing report image URL:', reportImageUrl);
        fetchImageWithRedirect(reportImageUrl);
        return;
      } else {
        console.error('AuthenticatedImage: File is not a report or missing ID', { type: file.type, reportId });
        setImgError(true);
        setIsLoading(false);
        return;
      }
    }

    // Check if this is a direct MinIO URL (contains presigned URL patterns)
    if (isMinIOUrl(src)) {
      // For MinIO URLs, use directly without authentication
      console.log('AuthenticatedImage: Detected MinIO URL, using directly');
      setImgSrc(src);
      setIsLoading(false);
      return;
    }

    // If it's an API URL, fetch with credentials
    if (src.includes('/api/v1/notebooks/') && src.includes('/images/')) {
      console.log('AuthenticatedImage: Detected notebook API URL, fetching with credentials');
      fetchImageWithCredentials(src);
    } else {
      // For external URLs, use directly
      console.log('AuthenticatedImage: Using external URL directly');
      setImgSrc(src);
      setIsLoading(false);
    }
  }, [src, file]);

  const isMinIOUrl = (url: string): boolean => {
    // Check if URL looks like a MinIO pre-signed URL
    const isMinIO = (
      url.includes('X-Amz-Algorithm') ||
      url.includes('X-Amz-Credential') ||
      url.includes('X-Amz-Signature') ||
      url.includes('?AWSAccessKeyId=') ||
      url.includes('&Signature=') ||
      (url.includes('localhost:9000') || url.includes('minio')) && url.includes('?')
    );

    console.log('AuthenticatedImage: isMinIOUrl check for', url.substring(0, 100), '... Result:', isMinIO);
    return isMinIO;
  };

  const fetchImageWithRedirect = async (url: string) => {
    try {
      console.log('AuthenticatedImage: Fetching image with redirect from:', url);

      // Fetch will automatically follow redirects by default
      const response = await fetch(url, {
        credentials: 'include',
        headers: {
          'Accept': 'image/*,*/*'
        }
      });

      // Check if response is OK and fetch the blob
      if (response.ok) {
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);
        console.log('AuthenticatedImage: Image fetched successfully, blob URL:', blobUrl);
        setImgSrc(blobUrl);
        setIsLoading(false);
        return;
      }

      // If response is not OK, throw error
      console.error('AuthenticatedImage: Failed to fetch image:', response.status, response.statusText);
      setImgError(true);
      setIsLoading(false);
    } catch (error) {
      console.error('AuthenticatedImage: Error fetching image with redirect:', error);
      setImgError(true);
      setIsLoading(false);
    }
  };

  const fetchImageWithCredentials = async (url: string) => {
    try {
      console.log('AuthenticatedImage: Fetching image with credentials:', url);

      const response = await fetch(url, {
        credentials: 'include',
        headers: {
          'Accept': 'image/*,*/*'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      console.log('AuthenticatedImage: Image fetched successfully, blob URL:', blobUrl);
      setImgSrc(blobUrl);
      setIsLoading(false);
    } catch (error) {
      console.error('AuthenticatedImage: Failed to fetch image:', error);
      setImgError(true);
      setIsLoading(false);
    }
  };

  // Cleanup blob URLs when component unmounts
  useEffect(() => {
    return () => {
      if (imgSrc && imgSrc.startsWith('blob:')) {
        URL.revokeObjectURL(imgSrc);
      }
    };
  }, [imgSrc]);

  return (
    <div className="my-4">
      {isLoading && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">Loading image...</span>
          </div>
        </div>
      )}

      {!isLoading && !imgError && (
        <img
          src={imgSrc}
          alt={alt || 'Image'}
          title={title}
          className="max-w-full h-auto rounded-lg border border-gray-200 shadow-sm"
          style={{ maxHeight: '500px' }}
          onError={() => {
            console.error('Image failed to load after processing:', { src: imgSrc, alt, title });
            setImgError(true);
          }}
          onLoad={() => {
            console.log('Image loaded successfully:', { src: imgSrc, alt });
          }}
        />
      )}

      {!isLoading && imgError && (
        <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 text-center text-gray-500">
          <div className="flex items-center justify-center space-x-2">
            <FileText className="h-5 w-5" />
            <span className="text-sm">Image could not be loaded</span>
          </div>
          {alt && <p className="text-xs mt-1 text-gray-400">{alt}</p>}
          <p className="text-xs mt-1 text-gray-400 break-all">Source: {src}</p>
        </div>
      )}
    </div>
  );
};

export default AuthenticatedImage;