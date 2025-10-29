"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Input } from "@/components/ui/input";
import { Plus, Trash2, Pencil } from "lucide-react";
import { saveCategories } from "@/app/actions/category-actions";

async function fetchSchema(): Promise<Category[]> {
  const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!API_URL) {
    throw new Error("API base URL is not defined in environment variables");
  }

  const res = await fetch(`${API_URL}/form-schema`);
  if (!res.ok) throw new Error("Failed to fetch schema");
  const data = await res.json();
  // Ensure subcategories is always an array of strings
  return (data.categories || []).map((cat: { name: string; fields: any[] }) => ({
    name: cat.name,
    subcategories: (cat.fields || []).map((field) =>
      typeof field === "string" ? field : field?.name ?? JSON.stringify(field)
    ),
  }));
}

type Subcategory = string;
type Category = {
  name: string;
  subcategories: Subcategory[];
};

type EditFormModalProps = {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
};

export function EditFormModal({ isOpen, onOpenChange }: EditFormModalProps) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [newCategory, setNewCategory] = useState("");
  const [newSubcategories, setNewSubcategories] = useState<{
    [key: string]: string;
  }>({});

  useEffect(() => {
    if (isOpen) {
      fetchSchema()
        .then(setCategories)
        .catch(() => setCategories([]));
    }
  }, [isOpen]);

  const handleAddCategory = () => {
    if (newCategory.trim() !== "") {
      const updatedCategories: Category[] = [
        ...categories,
        { name: newCategory, subcategories: [] },
      ];
      setCategories(updatedCategories);
      setNewCategory("");
    }
  };

  const handleDeleteCategory = (index: number) => {
    const updatedCategories = categories.filter((_, i) => i !== index);
    setCategories(updatedCategories);
  };

  const handleAddSubcategory = (categoryIndex: number) => {
    const subcategoryName = newSubcategories[categoryIndex]?.trim();
    if (subcategoryName) {
      const updatedCategories = [...categories];
      updatedCategories[categoryIndex].subcategories.push(subcategoryName);
      setCategories(updatedCategories);
      setNewSubcategories({ ...newSubcategories, [categoryIndex]: "" });
    }
  };

  const handleDeleteSubcategory = (
    categoryIndex: number,
    subIndex: number
  ) => {
    const updatedCategories = [...categories];
    updatedCategories[categoryIndex].subcategories.splice(subIndex, 1);
    setCategories(updatedCategories);
  };

  const handleSaveChanges = async () => {
    await saveCategories(categories);
    onOpenChange(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Edit Form Categories</DialogTitle>
          <DialogDescription>
            Add, edit, or remove categories and subcategories for the data
            collection form.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[70vh] min-h-[400px] overflow-y-auto pr-4 pl-4">
          <Accordion type="multiple" className="w-full">
            {categories.map((category, catIndex) => (
              <AccordionItem value={`item-${catIndex}`} key={catIndex}>
                <div className="flex items-center w-full">
                  <AccordionTrigger className="flex-grow hover:no-underline">
                      <span>{category.name}</span>
                  </AccordionTrigger>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteCategory(catIndex)}
                    className="mr-2"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                <AccordionContent>
                  <div className="space-y-2">
                    {category.subcategories.map((sub, subIndex) => (
                      <div
                        key={subIndex}
                        className="flex items-center justify-between pl-4"
                      >
                        <span>{sub}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            handleDeleteSubcategory(catIndex, subIndex)
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <div className="flex items-center gap-2 pl-4 pt-2">
                      <Input
                        placeholder="New subcategory"
                        value={newSubcategories[catIndex] || ""}
                        onChange={(e) =>
                          setNewSubcategories({
                            ...newSubcategories,
                            [catIndex]: e.target.value,
                          })
                        }
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleAddSubcategory(catIndex);
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        className="bg-white text-[#1E3A8A] hover:bg-gray-100"
                        onClick={() => handleAddSubcategory(catIndex)}
                      >
                        <Plus className="h-4 w-4 mr-1" /> Add
                      </Button>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>

          <div className="flex items-center gap-2 mt-4 mb-4">
            <Input
              placeholder="New category name"
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleAddCategory();
                }
              }}
            />
            <Button
                className="bg-white text-[#1E3A8A] hover:bg-gray-100"
                onClick={handleAddCategory}>
              <Plus className="h-4 w-4 mr-1" /> Add Category
            </Button>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSaveChanges}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
