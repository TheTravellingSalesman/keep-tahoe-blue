"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Loader2, Save } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  clearSubmissionData,
  getSubmissionData,
  saveSubmissionData,
  type SubmissionData as PersistedSubmissionData,
} from "@/lib/submission-storage";
import type { DataCollectionFormValues } from "@/lib/validators";


type OcrImage = {
  uuid: string;
  image: string;
  form: FormData;
};

type SubmissionData = PersistedSubmissionData<DataCollectionFormValues, OcrImage>;

type FormData = {
  categories: Category[];
};

type Category = {
  name: string;
  fields: TableRowData[];
};

type TableRowData = {
  name: string;
  value: number;
  status?: string;
};

export default function ReviewPage() {
  const [submissionData, setSubmissionDataState] = useState<SubmissionData | null>(null);
  const [currentTableData, setCurrentTableData] = useState<TableRowData[]>([]);
  const [isClient, setIsClient] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [images, setImages] = useState<OcrImage[]>([]);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const router = useRouter();

  useEffect(() => {
    setIsClient(true);
    let cancelled = false;

    void (async () => {
      let data = await getSubmissionData<DataCollectionFormValues, OcrImage>();
      if (!data && typeof window !== "undefined") {
        const legacyData = window.localStorage.getItem("submission-data");
        if (legacyData) {
          try {
            const parsed = JSON.parse(legacyData) as SubmissionData;
            await saveSubmissionData<DataCollectionFormValues, OcrImage>(parsed);
            window.localStorage.removeItem("submission-data");
            data = parsed;
          } catch (migrationError) {
            console.error("Failed to migrate legacy submission data:", migrationError);
          }
        }
      }
      if (!cancelled) {
        setSubmissionDataState(data);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (submissionData && Array.isArray(submissionData.ocrResults) && submissionData.ocrResults.length > 0) {
      setImages(submissionData.ocrResults);
    } else {
      setImages([]);
    }
  }, [submissionData]);

  useEffect(() => {
    if (images.length === 0) {
      setCurrentImageIndex(0);
      return;
    }
    if (currentImageIndex >= images.length) {
      setCurrentImageIndex(images.length - 1);
    }
  }, [images, currentImageIndex]);

  const currentImage = images[currentImageIndex];
  const totalImages = images.length;

  useEffect(() => {
    if (currentImage && currentImage.form && currentImage.form.categories) {
      const newTableData = currentImage.form.categories.flatMap(category => category.fields);
      setCurrentTableData(newTableData);
    } else {
      setCurrentTableData([]);
    }
  }, [currentImage]);

  const saveChanges = async () => {
    if (!submissionData || !submissionData.ocrResults || !currentImage) {
      return;
    }

    const updatedOcrResults = submissionData.ocrResults.map((image, index) => {
      if (index !== currentImageIndex) {
        return image;
      }

      const updatedCategories = image.form.categories.map(category => {
        const updatedFields = category.fields.map(field => {
          const updatedField = currentTableData.find(item => item.name === field.name);
          return updatedField ? { ...field, value: updatedField.value, status: updatedField.status } : field;
        });
        return { ...category, fields: updatedFields };
      });

      return { ...image, form: { ...image.form, categories: updatedCategories } };
    });

    const updatedSubmissionData: SubmissionData = {
      ...submissionData,
      ocrResults: updatedOcrResults,
    };

    setImages(updatedOcrResults);
    setSubmissionDataState(updatedSubmissionData);
    try {
      await saveSubmissionData<DataCollectionFormValues, OcrImage>(updatedSubmissionData);
    } catch (error) {
      console.error("Failed to persist submission data:", error);
    }
  };

  const handleCountChange = (index: number, value: string) => {
    const newTableData = [...currentTableData];
    newTableData[index].value = parseInt(value, 10) || 0;
    setCurrentTableData(newTableData);
  };

  const handleFocus = (index: number) => {
    const newTableData = [...currentTableData];
    const currentStatus = newTableData[index].status;
    if (currentStatus === 'needs-validation' || currentStatus === 'error') {
      newTableData[index].status = 'confident';
      setCurrentTableData(newTableData);
    }
  };

  const handlePrevious = () => {
    void (async () => {
      await saveChanges();
      setCurrentImageIndex(prev => Math.max(0, prev - 1));
    })();
  };

  const handleNext = () => {
    void (async () => {
      await saveChanges();
      setCurrentImageIndex(prev => Math.min(totalImages - 1, prev + 1));
    })();
  };

  const handleSubmitAll = async () => {
    setIsSubmitting(true);

    try {
      await saveChanges();

      const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
      if (!API_URL) {
        console.error("API base URL is not defined");
        setIsSubmitting(false);
        return;
      }

      const latestSubmissionData = await getSubmissionData<DataCollectionFormValues, OcrImage>();

      if (!latestSubmissionData || !latestSubmissionData.ocrResults || latestSubmissionData.ocrResults.length === 0) {
        console.error("Submission data is not available");
        setIsSubmitting(false);
        return;
      }

      const metadataPayload = Object.entries(latestSubmissionData.cleanupData).map(
        ([key, value]) => ({ name: key, value: String(value) })
      );

      const aggregatedCategories: { [categoryName: string]: { [fieldName: string]: number } } = {};

      latestSubmissionData.ocrResults.forEach((image) => {
        image.form.categories.forEach(category => {
          if (!aggregatedCategories[category.name]) {
            aggregatedCategories[category.name] = {};
          }
          category.fields.forEach(field => {
            const parsedValue =
              typeof field.value === "string"
                ? parseInt(field.value, 10)
                : Number(field.value);
            if (!aggregatedCategories[category.name][field.name]) {
              aggregatedCategories[category.name][field.name] = 0;
            }
            aggregatedCategories[category.name][field.name] += Number.isFinite(parsedValue) ? parsedValue : 0;
          });
        });
      });

      const cleanupDataPayload = Object.entries(aggregatedCategories).map(([categoryName, fields]) => ({
        category: categoryName,
        fields: Object.entries(fields).map(([fieldName, value]) => ({
          name: fieldName,
          value,
        })),
      }));

      const response = await fetch(`${API_URL}/generate-csv`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          metadata: metadataPayload,
          "clean-up-data": cleanupDataPayload,
        }),
      });

      if (!response.ok) {
        throw new Error(`API call failed with status: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;

      const contentDisposition = response.headers.get("Content-Disposition");
      let filename = "cleanup_data.csv";
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }
      a.download = filename;

      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      try {
        await clearSubmissionData();
      } catch (storageError) {
        console.error("Failed to clear submission data:", storageError);
      }
      setSubmissionDataState(null);
      setImages([]);
      setCurrentTableData([]);
      window.localStorage.removeItem("submission-data");
      window.localStorage.removeItem("orc-results");
      router.push("/submitted");
    } catch (error) {
      console.error("Error processing files:", error);
      setIsSubmitting(false);
    }
  };

  const getStatusClass = (status?: string) => {
    switch (status) {
      case 'needs-validation':
        return 'border-yellow-500';
      case 'error':
        return 'border-red-500';
      default:
        return '';
    }
  };

  return (
      <>
        {isSubmitting && (
            <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm">
              <Loader2 className="h-16 w-16 animate-spin text-primary" />
              <p className="mt-4 text-lg font-semibold">Submitting, please wait...</p>
            </div>
        )}
        <main className="container mx-auto p-4 md:p-8 flex flex-col h-screen">
          <div className="flex-shrink-0 text-center mb-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="lg" className="text-lg font-bold" disabled={isSubmitting}>
                  Submit All Files
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action will finalize and submit your cleanup data. You won't be able to make any changes after this.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleSubmitAll}>Continue</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
          <div className="flex items-center justify-center text-sm text-muted-foreground mb-6">
            <Save className="mr-2 h-4 w-4" />
            <span>Click Previous, Next, or Submit to save changes.</span>
          </div>
          <div className="flex-grow grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
            <div>
              <h2 className="text-2xl font-bold mb-4 font-headline">
                Review Image ({totalImages > 0 ? currentImageIndex + 1 : 0} of {totalImages})
              </h2>
              <div className="aspect-video relative rounded-lg overflow-hidden border">
                {currentImage ? (
                    <Image
                        src={`data:image/jpeg;base64,${currentImage.image}`}
                        alt={`Uploaded file ${currentImageIndex + 1}`}
                        fill
                        className="object-contain"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full bg-muted">
                      <p className="text-muted-foreground">No image to display</p>
                    </div>
                )}
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-4 font-headline">Categorize Items</h2>
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead className="w-[100px] text-right">Count</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {isClient && currentTableData.map((row, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-medium">{row.name}</TableCell>
                          <TableCell>
                            <Input
                                type="number"
                                value={row.value}
                                onChange={(e) => handleCountChange(index, e.target.value)}
                                onFocus={() => handleFocus(index)}
                                className={`text-right ${getStatusClass(row.status)}`}
                            />
                          </TableCell>
                        </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          </div>
          <div className="flex-shrink-0 flex justify-center items-center gap-4 mt-8 pb-4">
            <Button
                onClick={handlePrevious}
                disabled={currentImageIndex === 0 || isSubmitting}
            >
              <ChevronLeft />
              Previous
            </Button>
            <Button
                onClick={handleNext}
                disabled={totalImages === 0 || currentImageIndex === totalImages - 1 || isSubmitting}
            >
              Next
              <ChevronRight />
            </Button>
          </div>
        </main>
      </>
  );
}
