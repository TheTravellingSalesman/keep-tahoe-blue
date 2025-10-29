
"use client";

import { useRef, type DragEvent, useState } from "react";
import { UploadCloud, X, FileCheck2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { useToast } from "@/hooks/use-toast";



type FileUploaderProps = {
  files: File[];
  onFilesChange: (files: File[]) => void;
};

const MAX_FILES = 100;

export function FileUploader({ files, onFilesChange }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();


  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleFileSelect = (newFiles: FileList | null) => {
    if (newFiles) {
      const newFilesArray = Array.from(newFiles).filter(
          (file) =>
              !files.some(
                  (existingFile) =>
                      existingFile.name === file.name &&
                      existingFile.size === file.size
              )
      );

      if (files.length + newFilesArray.length > MAX_FILES) {
        toast({
          title: "Upload limit reached",
          description: `You can only upload a maximum of ${MAX_FILES} files.`,
          variant: "destructive",
        });
        const remainingSlots = MAX_FILES - files.length;
        if (remainingSlots > 0) {
          onFilesChange([...files, ...newFilesArray.slice(0, remainingSlots)]);
        }
      } else {
        onFilesChange([...files, ...newFilesArray]);
      }
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  return (
      <div>
        <header className="mb-6">
          <h2 className="text-2xl font-bold font-headline">
            Upload Data Card Images
          </h2>
          <p className="text-muted-foreground">
            Add data card images from your cleanup event (up to 100 images).
          </p>
        </header>
        <div className="flex flex-col gap-6">
          <div
              className={cn(
                  "flex cursor-pointer flex-col items-center justify-center p-8 border-2 border-dashed rounded-lg transition-colors duration-300",
                  isDragging
                      ? "border-primary bg-primary/10"
                      : "border-border/50 hover:border-primary/50"
              )}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
          >
            <UploadCloud
                className={cn(
                    "h-12 w-12 mb-4",
                    isDragging ? "text-primary" : "text-muted-foreground"
                )}
            />
            <p className="text-center font-semibold">
              {isDragging ? "Drop files here" : "Drag & drop files here"}
            </p>
            <p className="text-sm text-muted-foreground">or</p>
            <Button variant="link" className="text-primary p-0 h-auto">
              Browse files
            </Button>
            <input
                type="file"
                multiple
                ref={fileInputRef}
                className="hidden"
                onChange={(e) => handleFileSelect(e.target.files)}
                accept="image/*"
            />
          </div>

          {files.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-semibold text-lg">Uploaded Files</h3>
                <div className="max-h-48 overflow-y-auto pr-2 space-y-3">
                  {files.map((file, index) => (
                      <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-secondary/50 rounded-lg animate-in fade-in-0"
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <FileCheck2 className="h-5 w-5 text-primary flex-shrink-0" />
                          <span className="truncate text-sm" title={file.name}>
                      {file.name}
                    </span>
                        </div>
                        <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFile(index);
                            }}
                            className="p-1 rounded-full hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors"
                            aria-label={`Remove ${file.name}`}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                  ))}
                </div>
              </div>
          )}
        </div>
      </div>
  );
}
