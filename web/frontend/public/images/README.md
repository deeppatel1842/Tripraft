# Images Folder

This folder contains all the images used throughout the Tripraft website.

## Structure
```
images/
├── hero/           # Hero section images
├── features/       # Feature section icons/images
├── testimonials/   # User testimonials photos
└── general/        # General purpose images
```

## Usage
To use an image in your components:

```jsx
// For images in public/images folder
<img src="/images/hero/travel-bg.jpg" alt="Travel background" />
```

## Image Optimization Tips
- Use WebP format for better compression
- Optimize images before uploading (use tools like TinyPNG)
- Keep file sizes under 500KB for better performance
- Use descriptive filenames (e.g., `mountain-sunset.jpg` instead of `img001.jpg`)

## Recommended Image Sizes
- Hero backgrounds: 1920x1080px
- Feature icons: 512x512px
- Testimonial photos: 200x200px
- General images: 1200x800px
