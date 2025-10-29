
"use client";

import { useEffect, useState, useMemo, memo } from "react";
import type { UseFormReturn, SubmitHandler } from "react-hook-form";
import { format } from "date-fns";
import {
    CalendarIcon,
    Clock,
    Droplets,
    MapPin,
    Scale,
    Users,
} from "lucide-react";

import {
    type DataCollectionFormValues,
} from "@/lib/validators";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export const getInitialFormValues = (): DataCollectionFormValues => ({
    crewName: "",
    location: "",
    duration: null,
    totalPounds: null,
    date: new Date(),
    volunteers: null,
    zone: "Full",
    totalGallons: null,
});

type DataCollectionFormProps = {
    form: UseFormReturn<DataCollectionFormValues>;
    isClient: boolean;
};


export const DataCollectionForm = memo(function DataCollectionForm({
                                                                       form,
                                                                       isClient,
                                                                   }: DataCollectionFormProps) {

    const InputWithIcon = ({
                               icon,
                               children,
                           }: {
        icon: React.ReactNode;
        children: React.ReactNode;
    }) => (
        <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                {icon}
            </div>
            {children}
        </div>
    );

    return (
        <div>
            <header className="mb-6">
                <h2 className="text-2xl font-bold font-headline">
                    Cleanup Data Entry
                </h2>
                <p className="text-muted-foreground">
                    Enter the details of your cleanup event below.
                </p>
            </header>
            <Form {...form}>
                <div
                    className="space-y-6"
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="crewName"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold">Crew Name</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<Users className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                placeholder="e.g., Tahoe Keys Crew"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="location"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold">Location</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                placeholder="e.g., Pope Beach"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormField
                            control={form.control}
                            name="date"
                            render={({ field }) => (
                                <FormItem className="flex flex-col">
                                    <FormLabel className="font-bold">Date of Cleanup</FormLabel>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <FormControl>
                                                <Button
                                                    variant={"outline"}
                                                    className={cn(
                                                        "w-full pl-3 text-left font-normal justify-start bg-input border-input hover:bg-input/80",
                                                        !field.value && "text-muted-foreground"
                                                    )}
                                                >
                                                    <CalendarIcon className="mr-2 h-4 w-4" />
                                                    {isClient && field.value ? (
                                                        format(new Date(field.value), "PPP")
                                                    ) : (
                                                        <span>Pick a date</span>
                                                    )}
                                                </Button>
                                            </FormControl>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-auto p-0" align="start">
                                            <Calendar
                                                mode="single"
                                                selected={field.value ? new Date(field.value) : undefined}
                                                onSelect={field.onChange}
                                                disabled={(date) =>
                                                    date < new Date("1900-01-01")
                                                }
                                                initialFocus
                                            />
                                        </PopoverContent>
                                    </Popover>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="volunteers"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold"># of Volunteers</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<Users className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                type="number"
                                                placeholder="e.g., 15"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <FormField
                            control={form.control}
                            name="duration"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold">Duration (hours)</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<Clock className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                type="number"
                                                step="0.5"
                                                placeholder="e.g., 2.5"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="totalPounds"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold">Total Pounds</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<Scale className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                type="number"
                                                step="0.1"
                                                placeholder="e.g., 55.2"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <FormField
                            control={form.control}
                            name="totalGallons"
                            render={({ field }) => (
                                <FormItem>
                                    <FormLabel className="font-bold">Total Gallons</FormLabel>
                                    <FormControl>
                                        <InputWithIcon
                                            icon={<Droplets className="h-4 w-4 text-muted-foreground" />}
                                        >
                                            <Input
                                                type="number"
                                                step="0.1"
                                                placeholder="e.g., 20"
                                                {...field}
                                                value={field.value ?? ""}
                                                className="pl-10"
                                            />
                                        </InputWithIcon>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                    </div>

                    <FormField
                        control={form.control}
                        name="zone"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel className="font-bold">Zone Type</FormLabel>
                                <Select
                                    onValueChange={field.onChange}
                                    value={field.value ?? ""}
                                >
                                    <FormControl>
                                        <SelectTrigger className="bg-input border-input hover:bg-input/80">
                                            <SelectValue placeholder="Select a zone type" />
                                        </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                        <SelectItem value="Full">Full Zone</SelectItem>
                                        <SelectItem value="Half">Half Zone</SelectItem>
                                    </SelectContent>
                                </Select>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
            </Form>
        </div>
    );
});
