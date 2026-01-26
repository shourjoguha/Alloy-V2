import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth-store';
import { login } from '@/api/auth';
import { useUIStore } from '@/stores/ui-store';
import { useState } from 'react';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export const Route = createFileRoute('/login')({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { setToken, setUser, setAuthenticated } = useAuthStore();
  const { addToast } = useUIStore();
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    setIsLoading(true);
    try {
      const response = await login(data.email, data.password);
      setToken(response.access_token);
      setAuthenticated(true);
      // We also need to get user details, but login returns user_id. 
      // We can verify token to get full user details or just fetch it.
      // For now, we'll verify the token to get user data.
      // Actually, let's just navigate and let the app handle fetching user if needed,
      // or do a quick verify.
      
      // Let's verify to get user object
      try {
        const { verifyToken } = await import('@/api/auth');
        const user = await verifyToken(response.access_token);
        setUser(user);
      } catch (e) {
        console.error('Failed to fetch user details', e);
      }

      addToast({
        type: 'success',
        message: 'Logged in successfully',
      });
      navigate({ to: '/' });
    } catch (error: any) {
      addToast({
        type: 'error',
        message: error.response?.data?.detail || 'Login failed. Please check your credentials.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Login</CardTitle>
          <CardDescription>
            Enter your email and password to access your account
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="m@example.com"
                error={!!form.formState.errors.email}
                {...form.register('email')}
              />
              {form.formState.errors.email && (
                <p className="text-xs text-error">{form.formState.errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                error={!!form.formState.errors.password}
                {...form.register('password')}
              />
              {form.formState.errors.password && (
                <p className="text-xs text-error">{form.formState.errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" isLoading={isLoading}>
              Login
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <div className="text-center text-sm text-muted-foreground">
            Don't have an account?{' '}
            <Link to="/register" className="text-primary hover:underline">
              Register
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
