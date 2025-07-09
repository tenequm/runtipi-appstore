# ConvertX

ConvertX is a powerful self-hosted online file converter that supports over 1000 different file formats. Written with TypeScript, Bun and Elysia, it provides a modern web interface for converting files between various formats.

## Features

- **1000+ Format Support**: Convert between a vast array of file formats
- **Batch Processing**: Process multiple files at once
- **Password Protection**: Secure your instance with user authentication
- **Multiple Accounts**: Support for multiple user accounts
- **Auto-cleanup**: Automatically delete old files to save storage space
- **Modern UI**: Clean and intuitive web interface

## Supported Converters

ConvertX includes support for many powerful conversion tools:

- **Images**: ImageMagick, GraphicsMagick, Vips, libheif, Inkscape
- **Documents**: Pandoc, XeLaTeX, Calibre (e-books)
- **Video/Audio**: FFmpeg (supports ~472 input formats and ~199 output formats)
- **3D Assets**: Assimp
- **Vector Graphics**: Inkscape, Potrace, resvg, dvisvgm
- **Special Formats**: JPEG XL (libjxl), HEIF, SVG

## Configuration

### Environment Variables

- **Account Registration**: Control whether new users can register accounts
- **JWT Secret**: Secure token for authentication (auto-generated if not set)
- **Auto Delete**: Configure automatic cleanup of old files
- **FFMPEG Arguments**: Pass custom arguments to FFmpeg for video/audio conversion
- **Web Root**: Set a custom path for the web interface
- **Hide History**: Option to hide the conversion history page
- **Language**: Set the interface language

### Security Notes

- Always access the service over HTTPS in production
- The first account created becomes the admin account
- Set `ACCOUNT_REGISTRATION` to `false` if you only need one account
- Never set `HTTP_ALLOWED` or `ALLOW_UNAUTHENTICATED` to true in production

## Usage

1. Access ConvertX through your web browser
2. Create an account (first account has admin privileges)
3. Upload one or more files
4. Select the target format
5. Click convert and download your converted files

## Storage

All uploaded and converted files are stored in the `/app/data` directory within the container. Configure the auto-delete feature to automatically clean up old files and manage storage usage.