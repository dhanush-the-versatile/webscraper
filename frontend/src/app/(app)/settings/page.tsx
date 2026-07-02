"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { useUpdateProfile } from "@/hooks/use-api";
import { useAuthStore } from "@/store/auth";

const profileSchema = z.object({
  full_name: z.string().min(2, "Name is too short"),
});

const passwordSchema = z.object({
  password: z.string().min(8, "Use at least 8 characters"),
});

export default function SettingsPage() {
  const { user, setUser } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const updateProfile = useUpdateProfile();

  useEffect(() => setMounted(true), []);

  const profileForm = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    values: { full_name: user?.full_name ?? "" },
  });
  const passwordForm = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your account and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
          <CardDescription>Signed in as {user?.email}</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            onSubmit={profileForm.handleSubmit(async (values) => {
              const updated = await updateProfile.mutateAsync(values);
              setUser(updated);
            })}
          >
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full name</Label>
              <Input id="full_name" {...profileForm.register("full_name")} />
              {profileForm.formState.errors.full_name && (
                <p className="text-xs text-destructive">
                  {profileForm.formState.errors.full_name.message}
                </p>
              )}
            </div>
            <Button type="submit" size="sm" disabled={updateProfile.isPending}>
              {updateProfile.isPending ? "Saving…" : "Save profile"}
            </Button>
            {updateProfile.isSuccess && (
              <span className="ml-3 text-sm text-emerald-600 dark:text-emerald-400">Saved.</span>
            )}
          </form>

          <Separator className="my-6" />

          <form
            className="space-y-4"
            onSubmit={passwordForm.handleSubmit(async (values) => {
              await updateProfile.mutateAsync(values);
              passwordForm.reset({ password: "" });
            })}
          >
            <div className="space-y-1.5">
              <Label htmlFor="password">New password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                {...passwordForm.register("password")}
              />
              {passwordForm.formState.errors.password && (
                <p className="text-xs text-destructive">
                  {passwordForm.formState.errors.password.message}
                </p>
              )}
            </div>
            <Button type="submit" size="sm" variant="outline">
              Change password
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Appearance</CardTitle>
          <CardDescription>Choose how the app looks on this device.</CardDescription>
        </CardHeader>
        <CardContent>
          {mounted && (
            <div className="flex items-center gap-3">
              <Label className="w-24">Theme</Label>
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="system">System</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Data &amp; compliance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            This platform only collects publicly available professional information, honors
            robots.txt, and prefers official APIs (GitHub, Stack Exchange) over scraping.
          </p>
          <p>
            LinkedIn pages are never fetched — only public search-engine snippets of profiles
            are used. Configure search API keys server-side to enable live collection.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
