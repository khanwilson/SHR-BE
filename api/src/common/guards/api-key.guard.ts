import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class ApiKeyGuard implements CanActivate {
  constructor(private config: ConfigService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<{ headers: Record<string, string> }>();
    const key = request.headers['x-api-key'];
    const expected = this.config.get<string>('apiKey');

    if (!expected || key !== expected) {
      throw new UnauthorizedException('Invalid API key');
    }
    return true;
  }
}
