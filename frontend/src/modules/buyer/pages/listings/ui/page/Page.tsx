import { useEffect, useRef } from 'react';
import { ListingsGrid } from '../main/ListingsGrid';
import { pageOpened } from '../../model';

function Page() {
  const initializedRef = useRef(false);

  useEffect(() => {
    // Prevent double call in React StrictMode
    if (initializedRef.current) return;
    initializedRef.current = true;
    pageOpened();
  }, []);

  return <ListingsGrid />;
}

export const Listings = {
  route: '/listings',
  Page,
};
