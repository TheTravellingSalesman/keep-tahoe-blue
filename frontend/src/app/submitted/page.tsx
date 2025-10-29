
'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import tahoe from '@/app/images/tahoe.png';


export default function SubmittedPage() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    setIsLoading(true);
    router.push('/');
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-4 text-center">
      <div className="max-w-md w-full">
        <h1 className="text-3xl font-bold font-headline mb-2">
          Data has been submitted!
        </h1>
        <p className="text-muted-foreground mb-6">
          Thank you for helping Keep Tahoe Blue.
        </p>
        <img className="w-16 h-16 mx-auto mb-4" src={tahoe.src} alt="tahoe" />
        <Link href="/" passHref onClick={handleClick}>
          <Button size="lg" className="w-full text-lg">
            Upload More Data
          </Button>
        </Link>
      </div>
    </main>
  );
}
