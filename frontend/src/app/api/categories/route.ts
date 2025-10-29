import { NextRequest, NextResponse } from 'next/server';

type Subcategory = string;
type Category = {
  name: string;
  subcategories: Subcategory[];
};

export async function PUT(request: NextRequest) {
  try {
    const categories: Category[] = await request.json();
    
    console.log('Received categories:', categories);
    
    // Prepare schema as { categories: [{ name, fields }] }
    const schema = {
      categories: categories.map(cat => ({
        name: cat.name,
        fields: cat.subcategories.map(subcat => ({
          name: subcat
        })),
      })),
    };

    // Use server-side environment variable or fallback to localhost:8000
    const API_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    console.log('Using API URL:', API_URL);
    
    if (!API_URL) {
      return NextResponse.json(
        { error: "API base URL is not defined in environment variables" },
        { status: 500 }
      );
    }

    // Use fetch for server-side request
    console.log('Sending schema to backend:', JSON.stringify(schema, null, 2));
    
    const res = await fetch(`${API_URL}/form-schema`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(schema),
    });

    console.log('Backend response status:', res.status);

    if (!res.ok) {
      const errorText = await res.text();
      console.error('Backend error:', errorText);
      return NextResponse.json(
        { error: "Failed to save schema to backend", details: errorText },
        { status: res.status }
      );
    }

    const responseData = await res.json();
    console.log('Backend response data:', responseData);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error saving categories via backend:', error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}