import { Body, Controller, Delete, Get, Param, Patch, Query, UseGuards } from '@nestjs/common';
import { ApiKeyGuard } from '../common/guards/api-key.guard';
import { type UpdateCertificateInput, CertificatesService } from './certificates.service';

@Controller('certificates')
@UseGuards(ApiKeyGuard)
export class CertificatesController {
  constructor(private certificates: CertificatesService) {}

  @Get()
  findAll(
    @Query('page') page = '1',
    @Query('limit') limit = '20',
    @Query('search') search?: string,
  ) {
    return this.certificates.findAll(
      Math.max(1, parseInt(page, 10)),
      Math.min(100, parseInt(limit, 10)),
      search,
    );
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.certificates.findById(id);
  }

  @Patch(':id')
  update(@Param('id') id: string, @Body() body: UpdateCertificateInput) {
    return this.certificates.update(id, body);
  }

  @Delete(':id')
  remove(@Param('id') id: string) {
    return this.certificates.softDelete(id);
  }
}
