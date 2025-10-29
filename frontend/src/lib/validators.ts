import { z } from "zod";

export const dataCollectionSchema = z.object({
  crewName: z.string().min(1, { message: "Crew name is required." }),
  location: z.string().min(1, { message: "Location is required." }),
  duration: z.coerce
    .number({ invalid_type_error: "Duration must be a number." })
    .min(0, { message: "Duration must be a positive number." }),
  totalPounds: z.coerce
    .number({ invalid_type_error: "Pounds must be a number." })
    .min(0, { message: "Total pounds must be a positive number." }),
  date: z.date({
    required_error: "A date for the cleanup is required.",
  }),
  volunteers: z.coerce
    .number({ invalid_type_error: "Volunteers must be a number." })
    .int()
    .min(1, { message: "There must be at least one volunteer." }),
  zone: z.enum(["Full", "Half"], {
    required_error: "You need to select a zone type.",
  }),
  totalGallons: z.coerce
    .number({ invalid_type_error: "Gallons must be a number." })
    .min(0, { message: "Total gallons must be a positive number." }),
});

export type DataCollectionFormValues = z.infer<typeof dataCollectionSchema>;
