import { useState, useEffect, useRef } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';

const slides = [
  {
    id: 1,
    title: 'Intelligence that adapts to the body',
    subtitle: ''
  },
  {
    id: 2,
    title: 'The Problem',
    subtitle: "Today's fitness AI → Creative but unreliable OR Precise but robotic"
  },
  {
    id: 3,
    title: 'The Shift',
    subtitle: 'What if creativity and precision worked together'
  },
  {
    id: 4,
    title: 'The Product',
    subtitle: 'Alloy adapts in real time: personal, precise, transparent'
  },
  {
    id: 5,
    title: 'The Future',
    subtitle: 'Training is Hybrid'
  }
];

const particles = Array.from({ length: 30 }, (_, i) => ({
  id: i,
  left: Math.random() * 100,
  delay: Math.random() * 20,
  duration: 15 + Math.random() * 10
}));

export function LandingPage() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartX, setDragStartX] = useState(0);
  const [touchStartX, setTouchStartX] = useState(0);
  const navigate = useNavigate();
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isDragging) {
      const timer = setInterval(() => {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
      }, 8000);
      return () => clearInterval(timer);
    }
  }, [isDragging]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
      } else if (e.key === 'ArrowLeft') {
        setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    if (_hasHydrated && isAuthenticated) {
      navigate({ to: '/dashboard' });
    }
  }, [_hasHydrated, isAuthenticated, navigate]);

  const handleDotClick = (index: number) => {
    setCurrentSlide(index);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStartX(e.clientX);
  };

  const handleMouseMove = () => {
    if (!isDragging) return;
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dragEndX = e.clientX;
    const diff = dragStartX - dragEndX;

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
      } else {
        setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
      }
    }
    setIsDragging(false);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.touches[0].clientX);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    e.preventDefault();
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    const touchEndX = e.changedTouches[0].clientX;
    const diff = touchStartX - touchEndX;

    if (Math.abs(diff) > 50) {
      if (diff > 0) {
        setCurrentSlide((prev) => (prev + 1) % slides.length);
      } else {
        setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
      }
    }
  };

  const handleLogin = () => {
    if (!_hasHydrated) {
      navigate({ to: '/login' });
    } else if (isAuthenticated) {
      navigate({ to: '/dashboard' });
    } else {
      navigate({ to: '/login' });
    }
  };

  return (
    <div className="landing-container">
      <div className="background-particles">
        {particles.map((particle) => (
          <div
            key={particle.id}
            className="particle"
            style={{
              left: `${particle.left}%`,
              animationDelay: `${particle.delay}s`,
              animationDuration: `${particle.duration}s`
            }}
          />
        ))}
      </div>

      <div 
        className="slideshow-wrapper"
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="slides-track">
          {slides.map((slide, index) => (
            <div 
              key={slide.id} 
              className={`slide ${index === currentSlide ? 'active' : ''}`}
            >
              <div className="slide-content">
                <div className="slide-number">0{slide.id}</div>
                <h1 className="slide-title">{slide.title}</h1>
                {slide.subtitle && (
                  <p className="slide-subtitle">{slide.subtitle}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="slide-indicators">
          {slides.map((_, index) => (
            <button
              key={index}
              className={`indicator ${index === currentSlide ? 'active' : ''}`}
              onClick={() => handleDotClick(index)}
              aria-label={`Go to slide ${index + 1}`}
            />
          ))}
        </div>
      </div>

      <div className="landing-cta-container">
        <Button 
          variant="landing" 
          size="landing"
          onClick={handleLogin}
          disabled={!_hasHydrated}
          type="button"
        >
          <span className="cta-text">{!_hasHydrated ? 'Loading...' : (isAuthenticated ? 'Enter Dashboard' : 'Unlock')}</span>
          <div className="cta-glow"></div>
        </Button>
      </div>
    </div>
  );
}
