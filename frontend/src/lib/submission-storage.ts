export type SubmissionData<TForm, TResult> = {
  cleanupData: TForm;
  ocrResults?: TResult[];
};

const DB_NAME = "ktb-submission-db";
const DB_VERSION = 1;
const STORE_NAME = "submission";
const ENTRY_ID = "current";

type SubmissionRecord<TForm, TResult> = {
  id: string;
  data: SubmissionData<TForm, TResult>;
};

function getIndexedDB() {
  if (typeof window === "undefined") {
    return null;
  }
  if (!("indexedDB" in window)) {
    console.warn("IndexedDB is not supported in this environment.");
    return null;
  }
  return window.indexedDB;
}

async function openSubmissionDB(): Promise<IDBDatabase | null> {
  const indexedDB = getIndexedDB();
  if (!indexedDB) {
    return null;
  }

  return await new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => {
      console.error("Failed to open IndexedDB:", request.error);
      reject(request.error);
    };

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };

    request.onsuccess = () => resolve(request.result);
  });
}

export async function saveSubmissionData<TForm, TResult>(
  data: SubmissionData<TForm, TResult>
) {
  const db = await openSubmissionDB();
  if (!db) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put({ id: ENTRY_ID, data } as SubmissionRecord<TForm, TResult>);

    request.onerror = () => {
      console.error("Failed to save submission data:", request.error);
      reject(request.error);
    };

    transaction.oncomplete = () => {
      db.close();
      resolve();
    };

    transaction.onerror = () => {
      console.error("Transaction failed while saving submission data:", transaction.error);
      db.close();
      reject(transaction.error ?? request.error ?? new Error("Failed to save submission data"));
    };

    transaction.onabort = transaction.onerror;
  });
}

export async function getSubmissionData<TForm, TResult>(): Promise<
  SubmissionData<TForm, TResult> | null
> {
  const db = await openSubmissionDB();
  if (!db) {
    return null;
  }

  return await new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(ENTRY_ID);

    request.onerror = () => {
      console.error("Failed to read submission data:", request.error);
      reject(request.error);
    };

    request.onsuccess = () => {
      const record = request.result as SubmissionRecord<TForm, TResult> | undefined;
      resolve(record ? record.data : null);
    };

    transaction.oncomplete = () => {
      db.close();
    };

    transaction.onerror = () => {
      console.error("Transaction failed while reading submission data:", transaction.error);
      db.close();
      reject(transaction.error ?? request.error ?? new Error("Failed to read submission data"));
    };

    transaction.onabort = transaction.onerror;
  });
}

export async function clearSubmissionData() {
  const db = await openSubmissionDB();
  if (!db) {
    return;
  }

  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.delete(ENTRY_ID);

    request.onerror = () => {
      console.error("Failed to clear submission data:", request.error);
      reject(request.error);
    };

    transaction.oncomplete = () => {
      db.close();
      resolve();
    };

    transaction.onerror = () => {
      console.error("Transaction failed while clearing submission data:", transaction.error);
      db.close();
      reject(transaction.error ?? request.error ?? new Error("Failed to clear submission data"));
    };

    transaction.onabort = transaction.onerror;
  });
}
