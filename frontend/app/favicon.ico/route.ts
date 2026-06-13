const favicon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#1d4ed8"/>
  <path d="M20 13h18l8 8v30H20a4 4 0 0 1-4-4V17a4 4 0 0 1 4-4Z" fill="none" stroke="#fff" stroke-width="4"/>
  <path d="M38 13v10h10M24 31h16M24 39h16M24 47h9" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
</svg>`;

export function GET() {
  return new Response(favicon, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=86400"
    }
  });
}
