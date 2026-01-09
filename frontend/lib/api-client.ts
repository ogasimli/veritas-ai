/**
 * API Client Stub
 * 
 * Provides functions for interacting with the backend.
 * Currently returns mock data for development.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";


interface Job {
    id: string;
    status: "pending" | "processing" | "completed" | "failed";
    filename: string;
    created_at: string;
}

interface Finding {
    id: string;
    severity: "high" | "medium" | "low";
    category: string;
    message: string;
    source_context?: string;
}

export async function uploadDocument(file: File): Promise<Job> {
    console.log("Uploading file:", file.name);
    // Mock API call
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                id: Math.random().toString(36).substring(7),
                status: "pending",
                filename: file.name,
                created_at: new Date().toISOString(),
            });
        }, 1000);
    });
}

export async function getJob(id: string): Promise<Job> {
    console.log("Getting job:", id);
    return {
        id,
        status: "completed",
        filename: "financial_statement_2023.docx",
        created_at: new Date().toISOString(),
    };
}

export async function getJobFindings(id: string): Promise<Finding[]> {
    console.log("Getting findings for job:", id);
    return [
        {
            id: "1",
            severity: "high",
            category: "Numeric Validation",
            message: "Total Assets ($1,234,567) does not match sum of Current ($500,000) and Non-Current ($734,568) Assets. Difference: $1.",
            source_context: "Consolidated Balance Sheet, Page 4",
        },
        {
            id: "2",
            severity: "medium",
            category: "Logical Consistency",
            message: "Statement mentions 'no litigation' but Note 14 refers to an ongoing legal dispute with a supplier.",
            source_context: "Note 14 - Contingencies, Page 22",
        }
    ];
}
