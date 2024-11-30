from django.db import models

class SEINFRA_MG(models.Model):
    CODIGO = models.CharField(max_length=20)
    DESCRICAO_DE_SERVICO = models.TextField()
    UNIDADE = models.CharField(max_length=10, blank=True)
    CUSTO_UNITARIO = models.DecimalField(max_digits=10, decimal_places=2)
    REGIAO = models.CharField(max_length=50)

    class Meta:
        db_table = 'SEINFRA_MG'

    def __str__(self):
        return f"{self.CODIGO} - {self.DESCRICAO_DE_SERVICO}"
