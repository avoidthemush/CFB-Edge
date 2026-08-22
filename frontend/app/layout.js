import "./globals.css";
import { Sora, Inter } from "next/font/google";
import Sidebar from "./components/Sidebar";

const sora = Sora({
  subsets: ["latin"],
  weight: ["600", "700", "800"],
  variable: "--font-sora",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata = {
  title: "CFB Edge",
  description: "College football betting edge dashboard",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${sora.variable} ${inter.variable} antialiased`}>
        <div className="flex flex-col md:flex-row min-h-screen bg-[#1b212b]">
          <Sidebar />
          <div className="flex-1 min-w-0">{children}</div>
        </div>
      </body>
    </html>
  );
}