'use server';

import fs from 'fs/promises';
import path from 'path';
import yaml from 'js-yaml';
import fetch from 'node-fetch';

type Subcategory = string;
type Category = {
  name: string;
  subcategories: Subcategory[];
};

const yamlPath = path.join(process.cwd(), 'src', 'data', 'categories.yaml');


export async function saveCategories(categories: Category[]): Promise<void> {
  try {
    // Prepare schema as { categories: [{ name, fields }] }
    const schema = {
      categories: categories.map(cat => ({
        name: cat.name,
        fields: cat.subcategories.map(subcat =>
            ({
              name: subcat
            })),
      })),
    };

    const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!API_URL) {
      throw new Error("API base URL is not defined in environment variables");
    }

    // Use node-fetch for server-side fetch
    const res = await fetch(`${API_URL}/form-schema`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(schema),
    });

    if (!res.ok) {
      throw new Error("Failed to save schema to backend");
    }
  } catch (error) {
    console.error('Error saving categories via backend:', error);
    throw error;
  }
}
