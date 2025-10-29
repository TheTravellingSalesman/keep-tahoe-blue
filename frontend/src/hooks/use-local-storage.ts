"use client";

import { useState, useEffect, useCallback } from "react";

// A utility function to check if we are in a browser environment
const isBrowser = typeof window !== "undefined";

// This function attempts to get a value from localStorage.
// It's defined outside the hook to avoid being recreated on every render.
function getStorageValue<T>(key: string, initialValue: T): T {
  if (!isBrowser) {
    return initialValue;
  }
  try {
    const item = window.localStorage.getItem(key);
    return item ? JSON.parse(item) : initialValue;
  } catch (error) {
    console.warn(`Error reading localStorage key “${key}”:`, error);
    return initialValue;
  }
}

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  
  // The state is initialized with a function that runs only once.
  const [storedValue, setStoredValue] = useState<T>(() => {
    return getStorageValue(key, initialValue);
  });

  // The setValue function is memoized with useCallback to prevent
  // it from being recreated on every render.
  const setValue = useCallback((value: T | ((val: T) => T)) => {
    try {
      // Allow value to be a function so we have the same API as useState
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;
      // Save state
      setStoredValue(valueToStore);
      // Save to local storage
      if (isBrowser) {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting localStorage key “${key}”:`, error);
    }
  }, [key, storedValue]);

  // This effect will only run if the key changes, which is unlikely.
  // It handles cases where the localStorage might be updated in another tab.
  useEffect(() => {
    if (isBrowser) {
      const handleStorageChange = (event: StorageEvent) => {
        if (event.key === key) {
           setStoredValue(event.newValue ? JSON.parse(event.newValue) : initialValue);
        }
      };
      window.addEventListener('storage', handleStorageChange);
      return () => {
        window.removeEventListener('storage', handleStorageChange);
      };
    }
  }, [key, initialValue]);


  return [storedValue, setValue];
}
