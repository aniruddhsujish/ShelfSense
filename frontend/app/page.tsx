"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";

interface Book {
  book_id: string;
  title: string;
  authors: string[];
  description: string;
  thumbnail: string;
  score: string;
  explanation: {
    similar: string[];
    different: string[];
    recommended_because: string;
  };
}

interface RecommendResponse {
  query_book: Book;
  recommendations: Book[];
}
export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [discoverResults, setDiscoverResults] = useState<Book[]>([]);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [activeTab, setActiveTab] = useState<"search" | "discover">("discover");
  const [suggestions, setSuggestions] = useState<
    { title: string; authors: string[] }[]
  >([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const suggestCache = useRef<
    Map<string, { title: string; authors: string[] }[]>
  >(new Map());

  useEffect(() => {
    handleDiscover();
  }, []);

  async function handleSearch(searchTitle?: string) {
    const titleToSearch = searchTitle ?? query;
    if (!titleToSearch.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch("http://localhost:8000/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: titleToSearch, limit: 5 }),
      });

      if (!response.ok) {
        setError("Book not found. Try a different title.");
        return;
      }

      const data = await response.json();
      setResults(data);

      await handleRate(data.query_book.book_id, data.query_book.title, 1);
    } catch {
      setError("Could not connect to server");
    } finally {
      setLoading(false);
    }
  }

  async function handleRate(bookId: string, title: string, rating: number) {
    setRatings((prev) => ({ ...prev, [bookId]: rating }));
    await fetch("http://localhost:8000/api/rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ book_id: bookId, title, rating }),
    });
  }

  async function handleDiscover() {
    setDiscoverLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/api/discover?limit=5",
      );
      const data = await response.json();
      setDiscoverResults(data?.books ?? []);
    } finally {
      setDiscoverLoading(false);
    }
  }

  async function fetchSuggestions(value: string) {
    if (value.length < 2) {
      setSuggestions([]);
      return;
    }

    if (suggestCache.current.has(value)) {
      setSuggestions(suggestCache.current.get(value)!);
      return;
    }

    abortRef.current?.abort();
    abortRef.current = new AbortController();

    try {
      const resp = await fetch(
        `http://localhost:8000/api/suggest?q=${encodeURIComponent(value)}`,
        { signal: abortRef.current.signal },
      );
      const data = await resp.json();
      suggestCache.current.set(value, data.suggestions ?? []);
      setSuggestions(data.suggestions ?? []);
    } catch (e) {
      if ((e as Error).name !== "AbortError") throw e;
    }
  }

  return (
    <main className="min-h-screen bg-gray-950">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-8 pt-6">
          <h1 className="text-6xl font-black text-white tracking-tight mb-3">
            ShelfSense
          </h1>
          <p className="text-gray-400 text-lg">
            Find books similar to the ones you love
          </p>
        </div>

        <div className="flex gap-1 bg-gray-900 border border-gray-800 p-1 rounded-xl mb-8">
          <button
            onClick={() => setActiveTab("discover")}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === "discover"
                ? "bg-gray-800 text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Discover
          </button>
          <button
            onClick={() => setActiveTab("search")}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === "search"
                ? "bg-gray-800 text-white"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Search
          </button>
        </div>

        {activeTab === "search" && (
          <>
            {/* Search section */}
            <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8 mb-8">
              <h2 className="text-lg font-semibold text-gray-200 mb-1">
                Search
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                Enter a title to find semantically similar books
              </p>
              <div className="relative">
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      if (debounceRef.current)
                        clearTimeout(debounceRef.current);
                      debounceRef.current = setTimeout(
                        () => fetchSuggestions(e.target.value),
                        300,
                      );
                    }}
                    onBlur={() => setTimeout(() => setSuggestions([]), 150)}
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                    placeholder="Enter a book title..."
                    className="border border-gray-700 bg-gray-800 rounded-xl px-4 py-3 text-gray-100 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full"
                  />
                  <button
                    onClick={() => handleSearch()}
                    disabled={loading}
                    className="bg-blue-600 text-white px-6 py-3 rounded-xl text-sm font-medium hover:bg-blue-700 active:bg-blue-800 transition-colors disabled:opacity-50"
                  >
                    {loading ? "Searching..." : "Search"}
                  </button>
                </div>
                {suggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900 border border-gray-700 rounded-xl overflow-hidden z-10 shadow-xl">
                    {suggestions.map((s, index) => (
                      <button
                        key={`${s.title}-${index}`}
                        onMouseDown={() => {
                          setQuery(s.title);
                          setSuggestions([]);
                          handleSearch(s.title);
                        }}
                        className="w-full px-4 py-3 text-left hover:bg-gray-800 transition-colors border-b border-gray-800 last:border-0"
                      >
                        <p className="text-sm text-gray-200">{s.title}</p>
                        <p className="text-xs text-gray-500">
                          {s.authors.join(", ")}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {error && <p className="text-red-500 text-sm mt-3">{error}</p>}
            </div>

            {/* Results */}
            {loading && (
              <div className="space-y-4 mb-8">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-gray-900 rounded-2xl border border-gray-100 p-6 animate-pulse"
                  >
                    <div className="flex gap-4">
                      <div className="w-16 h-24 bg-gray-800 rounded-lg shrink-0" />
                      <div className="flex-1 space-y-3">
                        <div className="h-4 bg-gray-800 rounded w-1/2" />
                        <div className="h-3 bg-gray-800 rounded w-1/4" />
                        <div className="h-3 bg-gray-800 rounded w-full" />
                        <div className="h-3 bg-gray-800 rounded w-3/4" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {results && (
              <div className="space-y-4">
                <h2 className="text-lg font-semibold text-gray-300">
                  Books similar to{" "}
                  <span className="text-blue-600">
                    {results.query_book.title}
                  </span>
                </h2>
                {results.recommendations.map((book) => (
                  <div
                    key={book.book_id}
                    className="bg-gray-900 rounded-2xl border border-gray-800 p-6 hover:shadow-md transition-shadow duration-200"
                  >
                    <div className="flex gap-4">
                      {book.thumbnail && (
                        <div className="relative w-16 h-24 flex-shrink-0">
                          <Image
                            src={book.thumbnail.replace("http://", "https://")}
                            alt={book.title}
                            fill
                            className="object-cover rounded-lg"
                          />
                        </div>
                      )}
                      <div className="flex-1 ml-4">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className="font-semibold text-white">
                            {book.title}
                          </h3>
                          <span className="text-xs text-indigo-400 bg-indigo-950 px-2.5 py-0.5 rounded-full font-medium">
                            {Math.round(Number(book.score) * 100)}% match
                          </span>
                        </div>
                        <p className="text-gray-500 text-sm mb-3">
                          {book.authors.join(", ")}
                        </p>
                        <p className="text-gray-300 text-sm leading-relaxed">
                          {book.explanation.recommended_because}
                        </p>
                        <details className="text-sm">
                          <summary className="text-blue-400 cursor-pointer hover:text-blue-700 font-medium">
                            Why this book?
                          </summary>
                          <div className="mt-3 space-y-3">
                            <div>
                              <p className="font-medium text-gray-300 mb-1">
                                Similar
                              </p>
                              <ul className="space-y-1">
                                {book.explanation.similar.map((point, i) => (
                                  <li
                                    key={i}
                                    className="text-gray-500 flex gap-2"
                                  >
                                    <span className="text-green-400">✓</span>{" "}
                                    {point}
                                  </li>
                                ))}
                              </ul>
                            </div>
                            <div>
                              <p className="font-medium text-gray-300 mb-1">
                                Different
                              </p>
                              <ul className="space-y-1">
                                {book.explanation.different.map((point, i) => (
                                  <li
                                    key={i}
                                    className="text-gray-500 flex gap-2"
                                  >
                                    <span className="text-orange-400">≠</span>{" "}
                                    {point}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        </details>
                        <div className="flex gap-3 mt-4 pt-4 border-t border-gray-800">
                          <button
                            onClick={() =>
                              handleRate(book.book_id, book.title, 1)
                            }
                            className={`flex items-center gap-1 text-sm transition-colors ${
                              ratings[book.book_id] === 1
                                ? "text-green-500 font-semibold"
                                : "text-gray-400 hover:text-green-500"
                            }`}
                          >
                            👍 Like
                          </button>
                          <button
                            onClick={() =>
                              handleRate(book.book_id, book.title, -1)
                            }
                            className={`flex items-center gap-1 text-sm transition-colors ${
                              ratings[book.book_id] === -1
                                ? "text-red-400 font-semibold"
                                : "text-gray-400 hover:text-red-400"
                            }`}
                          >
                            👎 Dislike
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        {/* Discover section */}
        {activeTab === "discover" && (
          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-200">
                  Discover for you
                </h2>
                <p className="text-gray-400 text-sm">
                  Based on your taste profile
                </p>
              </div>
              <button
                onClick={handleDiscover}
                disabled={discoverLoading}
                className=" border border-gray-700 text-gray-400 px-4 py-1.5 rounded-lg text-sm hover:border-gray-500 hover:text-gray-200 transition-colors disabled:opacity-50"
              >
                {discoverLoading ? "Loading..." : "Refresh"}
              </button>
            </div>

            {discoverLoading ? (
              <p className="text-gray-400 text-sm">Loading...</p>
            ) : discoverResults?.length === 0 ? (
              <p className="text-gray-400 text-sm">
                Rate some books to get personalised recommendations
              </p>
            ) : (
              <div className="space-y-4">
                {discoverResults?.map((book) => (
                  <div
                    key={book.book_id}
                    className="flex gap-4 py-4 border-t border-gray-800"
                  >
                    {book.thumbnail && (
                      <div className="relative w-12 h-16 flex-shrink-0">
                        <Image
                          src={book.thumbnail.replace("http://", "https://")}
                          alt={book.title}
                          fill
                          className="object-cover rounded"
                        />
                      </div>
                    )}
                    <div className="flex-1 ml-2">
                      <h3 className="font-medium text-white text-sm">
                        {book.title}
                      </h3>
                      <p className="text-gray-400 text-xs mb-2">
                        {book.authors.join(", ")}
                      </p>
                      <p className="text-gray-400 text-xs leading-relaxed mb-2 line-clamp-3">
                        {book.description}
                      </p>
                      <div className="flex gap-3">
                        <button
                          onClick={() =>
                            handleRate(book.book_id, book.title, 1)
                          }
                          className={`text-xs transition-colors ${
                            ratings[book.book_id] === 1
                              ? "text-green-500 font-semibold"
                              : "text-gray-400 hover:text-green-500"
                          }`}
                        >
                          👍 Like
                        </button>
                        <button
                          onClick={() =>
                            handleRate(book.book_id, book.title, -1)
                          }
                          className={`text-xs transition-colors ${
                            ratings[book.book_id] === -1
                              ? "text-red-400 font-semibold"
                              : "text-gray-400 hover:text-red-400"
                          }`}
                        >
                          👎 Dislike
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
