"use client";

import { useState, useCallback } from "react";
import { useForm, type SubmitHandler } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Pencil, Upload } from "lucide-react";
import { EditFormModal } from "@/components/edit-form-modal";
import { DataCollectionForm, getInitialFormValues } from "@/components/data-collection-form";
import { FileUploader } from "@/components/file-uploader";
import {
    dataCollectionSchema,
    type DataCollectionFormValues,
} from "@/lib/validators";
import { saveSubmissionData } from "@/lib/submission-storage";

type ImageFile = {
    uuid: string;
    name: string;
    type: string;
    size: number;
    base64: string;
    dataUrl: string;
};

// New types for OCR response persistence
type OcrField = { name: string; value: string; status: string };
type OcrCategory = { name: string; fields: OcrField[] };
export type OcrResult = { uuid: string; image: string; form: { categories: OcrCategory[] } };

export default function Home() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isClient, setIsClient] = useState(false);
    const [files, setFiles] = useState<File[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const router = useRouter();

    const form = useForm<DataCollectionFormValues>({
        resolver: zodResolver(dataCollectionSchema),
        defaultValues: getInitialFormValues(),
    });

    useState(() => {
        setIsClient(true);
    });

    const onSubmit: SubmitHandler<DataCollectionFormValues> = async (data) => {
        if (files.length === 0) {
            alert("Please upload at least one image before submitting.");
            return;
        }

        setIsSubmitting(true);
        const imagePromises = files.map((file) => {
            return new Promise<ImageFile>((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const base64 = (event.target?.result as string).split(",")[1];
                    const dataUrl = event.target?.result as string;
                    resolve({
                        uuid: crypto.randomUUID(),
                        name: file.name,
                        type: file.type,
                        size: file.size,
                        base64,
                        dataUrl,
                    });
                };
                reader.onerror = (error) => reject(error);
                reader.readAsDataURL(file);
            });
        });

        try {
            const images = await Promise.all(imagePromises);

            const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
            if (!API_URL) throw new Error("API base URL is not defined");

            // Create a comma-separated string of UUIDs for metadata
            const metadata = images.map(img => img.uuid).join(',');

            const filesPayload = images.map(img => ({
                uuid: img.uuid,
                name: img.name,
                type: img.type,
                size: img.size,
                base64: img.base64,
            }));

            const response = await fetch(`${API_URL}/upload`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    files: filesPayload,
                    metadata: metadata
                })
            });

            if (!response.ok) {
                // Log error and do not continue
                const errorText = await response.text();
                console.error("Upload failed:", errorText);
                setIsSubmitting(false);
                return;
            }

            const uploadData = await response.json(); // { results: [...] }
            await saveSubmissionData<DataCollectionFormValues, OcrResult>({
                cleanupData: data,
                ocrResults: uploadData.results,
            });
            if (typeof window !== "undefined") {
                window.localStorage.removeItem("submission-data");
            }

            router.push("/review");
        } catch (error) {
            console.error("Error processing files:", error);
            setIsSubmitting(false);
        }
    };

    const memoizedSetIsSubmitting = useCallback(setIsSubmitting, []);


    return (
        <>
            <main className="container mx-auto p-4 md:p-8 pb-24">
                <div className="absolute top-4 right-4">
                    <Button variant="outline" onClick={() => setIsModalOpen(true)}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit Form
                    </Button>
                </div>
                <header className="text-center mb-12">
                    <h1 className="font-headline text-4xl md:text-5xl font-bold tracking-tight">
                        Keep Tahoe Blue
                    </h1>
                    <p className="text-lg text-muted-foreground mt-2">
                        Citizen Science Data Collection
                    </p>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 max-w-6xl mx-auto">
                    <DataCollectionForm
                        form={form}
                        isClient={isClient}
                    />
                    <div className="space-y-8">
                        <FileUploader files={files} onFilesChange={setFiles} />
                        
                    </div>
                </div>
                <div className="flex justify-center mt-12">
                    <Button
                        onClick={form.handleSubmit(onSubmit)}
                        size="lg"
                        className="w-full md:w-auto"
                        disabled={isSubmitting}
                    >
                        <Upload className="mr-2" />
                        {isSubmitting ? "Submitting..." : "Submit Data"}
                    </Button>
                </div>
            </main>
            <EditFormModal isOpen={isModalOpen} onOpenChange={setIsModalOpen} />
        </>
    );
}
