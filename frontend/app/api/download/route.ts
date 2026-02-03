import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(req: NextRequest) {
    const searchParams = req.nextUrl.searchParams;
    const filePath = searchParams.get('path');

    if (!filePath) {
        return NextResponse.json({ error: 'Path is required' }, { status: 400 });
    }

    try {
        if (!fs.existsSync(filePath)) {
            return NextResponse.json({ error: 'File not found' }, { status: 404 });
        }

        const fileBuffer = fs.readFileSync(filePath);
        const fileName = path.basename(filePath);

        // Determine mime type
        let contentType = 'application/octet-stream';
        if (fileName.toLowerCase().endsWith('.pdf')) contentType = 'application/pdf';
        else if (fileName.toLowerCase().endsWith('.png')) contentType = 'image/png';
        else if (fileName.toLowerCase().endsWith('.jpg') || fileName.toLowerCase().endsWith('.jpeg')) contentType = 'image/jpeg';

        // Use 'inline' for preview, 'attachment' for download
        const preview = searchParams.get('preview');
        const disposition = preview === 'true' ? 'inline' : 'attachment';

        return new NextResponse(fileBuffer, {
            headers: {
                'Content-Type': contentType,
                'Content-Disposition': `${disposition}; filename="${fileName}"`,
            },
        });
    } catch (error) {
        console.error('Error downloading file:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
