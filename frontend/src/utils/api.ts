declare global {
    interface Window {
        backend_host?: string;
    }
}

async function getBaseUrl(): Promise<string> {
    if (window.backend_host) {
        return window.backend_host;
    }

    try {
        const response = await fetch("/health");
        const data = await response.json();
        if (data.backend_host) {
            window.backend_host = data.backend_host;
            return data.backend_host;
        }
    } catch (error) {
        console.error("Failed to fetch backend host:", error);
    }

    throw new Error("BACKEND_HOST environment variable is not configured. Please set it in your .env.local file.");
}

export async function getBaseHttpUrl(): Promise<string> {
    return "http://" + await getBaseUrl();
}

export async function getBaseWsUrl(): Promise<string> {
    return "ws://" + await getBaseUrl();
}