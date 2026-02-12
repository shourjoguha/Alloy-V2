import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { useAuthStore } from '@/stores/auth-store';
import { login } from '@/api/auth';
import { useUIStore } from '@/stores/ui-store';
import { useState } from 'react';
import { AuthBackground } from '@/components/auth/AuthBackground';
import '@/styles/landing.css';

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
      
      console.log('[Login] Login successful, setting auth state', {
        userId: response.user_id,
        tokenLength: response.access_token.length
      });
      
      setToken(response.access_token);
      setAuthenticated(true);
      
      setUser({
        id: response.user_id,
        email: data.email,
        is_active: true,
        name: null
      });

      addToast({
        type: 'success',
        message: 'Logged in successfully',
      });
      
      console.log('[Login] Navigating to dashboard');
      navigate({ to: '/dashboard' });
    } catch (error: unknown) {
      console.error('[Login] Login failed:', error);
      const err = error as { response?: { data?: { detail?: string } } };
      addToast({
        type: 'error',
        message: err.response?.data?.detail || 'Login failed. Please check your credentials.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthBackground>
      <div className="auth-container">
        <Card variant="auth">
          <CardHeader>
            <CardTitle>Welcome Back</CardTitle>
            <CardDescription>Enter your credentials to access Alloy</CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={form.handleSubmit(onSubmit)} className="auth-form">
              <div className="form-group">
                <Label htmlFor="email" className="auth-label">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  variant="auth"
                  error={!!form.formState.errors.email}
                  {...form.register('email')}
                />
                {form.formState.errors.email && (
                  <p className="auth-error">{form.formState.errors.email.message}</p>
                )}
              </div>

              <div className="form-group">
                <Label htmlFor="password" className="auth-label">Password</Label>
                <Input
                  id="password"
                  type="password"
                  variant="auth"
                  error={!!form.formState.errors.password}
                  {...form.register('password')}
                />
                {form.formState.errors.password && (
                  <p className="auth-error">{form.formState.errors.password.message}</p>
                )}
              </div>

              <Button type="submit" variant="auth" size="lg" isLoading={isLoading}>
                Login
              </Button>
            </form>
          </CardContent>

          <CardFooter>
            <p className="auth-footer-text">
              Don't have an account?{' '}
              <Link to="/register" className="auth-link">
                Register
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </AuthBackground>
  );
}
