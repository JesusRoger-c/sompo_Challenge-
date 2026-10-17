/*
 * SomPrev Risk — sensor de inclinação do estande (NEXT 2026)
 * ---------------------------------------------------------
 * Lê o MPU6050 preso embaixo do trator, calcula a inclinação em graus e publica
 * numa rede Wi-Fi própria. O notebook se conecta nessa rede e a tela do placar
 * (placar.html) lê o ângulo daqui.
 *
 * POR QUE REDE PRÓPRIA (SoftAP) E NÃO O HOTSPOT DO CELULAR
 *   Numa feira o Wi-Fi é o primeiro a falhar. Com SoftAP o ESP32 cria a própria
 *   rede: não depende de internet, de roteador, nem do celular de ninguém. O
 *   notebook conecta direto no ESP32 e a API do modelo roda em localhost, que
 *   funciona sem rede nenhuma. Zero dependência externa no dia.
 *
 * POR QUE SEM BIBLIOTECA DE MPU6050
 *   O MPU6050 é lido direto por I2C, com Wire.h, que já vem no core do ESP32.
 *   Nenhuma biblioteca para instalar = nenhuma biblioteca para dar errado na
 *   véspera. São só três registradores.
 *
 * LIGAÇÃO (4 jumpers fêmea-fêmea)
 *   MPU6050 VCC -> ESP32 3V3     (3,3 V, NUNCA 5 V)
 *   MPU6050 GND -> ESP32 GND
 *   MPU6050 SCL -> ESP32 GPIO 22
 *   MPU6050 SDA -> ESP32 GPIO 21
 *
 * COMO GRAVAR
 *   Arduino IDE -> Preferências -> URL adicional de placas:
 *     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
 *   Ferramentas -> Placa -> "ESP32 Dev Module". Porta -> a que aparecer ao plugar.
 *   (Mac: se a porta não aparecer, instale o driver CP210x da Silicon Labs.)
 *
 * ENDEREÇOS DEPOIS DE LIGADO
 *   Rede Wi-Fi:  SomPrev-Risk     senha: somprev2026
 *   Dados:       http://192.168.4.1/dados     -> JSON com o ângulo
 *   Re-zerar:    http://192.168.4.1/zerar     -> define a posição atual como 0°
 */

#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>

// ----------------------------------------------------------------- ajustes
const char* REDE_NOME  = "SomPrev-Risk";
const char* REDE_SENHA = "somprev2026";      // mínimo 8 caracteres

const int PINO_SDA = 21;
const int PINO_SCL = 22;

const uint8_t MPU = 0x68;                    // endereço I2C do MPU6050
const uint8_t REG_ACORDAR = 0x6B;
const uint8_t REG_ESCALA  = 0x1C;
const uint8_t REG_ACEL    = 0x3B;
const float   LSB_POR_G   = 16384.0;         // escala ±2 g

const float SUAVIZACAO = 0.18;               // 0 = travado, 1 = sem suavizar
const float TOLERANCIA_ESTAVEL = 0.8;        // graus de variação que ainda conta como parado
const unsigned long MS_PARA_ESTABILIZAR = 600;

// ----------------------------------------------------------------- estado
WebServer servidor(80);
float anguloSuave = 0.0;
float anguloZero  = 0.0;                     // inclinação da bancada quando o trator está "plano"
float ultimoParaEstabilidade = 0.0;
unsigned long desdeQuandoParado = 0;
bool sensorOk = false;

// ----------------------------------------------------------------- MPU6050
void escreverRegistrador(uint8_t reg, uint8_t valor) {
  Wire.beginTransmission(MPU);
  Wire.write(reg);
  Wire.write(valor);
  Wire.endTransmission();
}

bool iniciarSensor() {
  Wire.begin(PINO_SDA, PINO_SCL);
  Wire.setClock(400000);
  Wire.beginTransmission(MPU);
  if (Wire.endTransmission() != 0) return false;   // ninguém respondeu nesse endereço
  escreverRegistrador(REG_ACORDAR, 0x00);          // tira do modo de dormir
  escreverRegistrador(REG_ESCALA, 0x00);           // ±2 g: a faixa mais sensível, que é o que queremos
  delay(100);
  return true;
}

/* Lê os três eixos do acelerômetro e devolve a inclinação em relação ao plano
 * horizontal, em graus. Parado e nivelado dá 0; tombando para qualquer lado o
 * valor sobe. Usa a gravidade como referência — por isso o trator precisa estar
 * em repouso no momento da leitura (o que é exatamente o caso aqui). */
bool lerAngulo(float& graus) {
  Wire.beginTransmission(MPU);
  Wire.write(REG_ACEL);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)MPU, 6, true) != 6) return false;

  int16_t bx = (Wire.read() << 8) | Wire.read();
  int16_t by = (Wire.read() << 8) | Wire.read();
  int16_t bz = (Wire.read() << 8) | Wire.read();

  float ax = bx / LSB_POR_G;
  float ay = by / LSB_POR_G;
  float az = bz / LSB_POR_G;

  float horizontal = sqrt(ax * ax + ay * ay);
  graus = atan2(horizontal, fabs(az)) * 180.0 / PI;
  return true;
}

// ----------------------------------------------------------------- rotas HTTP
void cabecalhosCors() {
  servidor.sendHeader("Access-Control-Allow-Origin", "*");
  servidor.sendHeader("Cache-Control", "no-store");
}

void rotaDados() {
  float mostrado = anguloSuave - anguloZero;
  if (mostrado < 0) mostrado = 0;                       // abaixo do zero não faz sentido aqui

  bool estavel = (millis() - desdeQuandoParado) > MS_PARA_ESTABILIZAR;

  char corpo[160];
  snprintf(corpo, sizeof(corpo),
           "{\"ok\":%s,\"angulo\":%.1f,\"estavel\":%s,\"bruto\":%.1f,\"ligado_ha_s\":%lu}",
           sensorOk ? "true" : "false", mostrado, estavel ? "true" : "false",
           anguloSuave, millis() / 1000);

  cabecalhosCors();
  servidor.send(200, "application/json", corpo);
}

void rotaZerar() {
  anguloZero = anguloSuave;                             // posição atual passa a ser o "plano"
  cabecalhosCors();
  servidor.send(200, "application/json", "{\"ok\":true,\"mensagem\":\"zerado\"}");
}

void rotaRaiz() {
  cabecalhosCors();
  servidor.send(200, "text/plain",
                "SomPrev Risk - sensor de inclinacao\n"
                "/dados  -> leitura em JSON\n"
                "/zerar  -> define a posicao atual como 0 grau\n");
}

// ----------------------------------------------------------------- ciclo
void setup() {
  Serial.begin(115200);
  delay(300);

  sensorOk = iniciarSensor();
  Serial.println(sensorOk ? "MPU6050 respondeu." : "MPU6050 NAO respondeu - confira os 4 jumpers.");

  // Primeira leitura vira a referência de "plano": monte o diorama nivelado e
  // só então ligue o ESP32. Dá para corrigir depois chamando /zerar.
  if (sensorOk) {
    float g;
    for (int i = 0; i < 40 && lerAngulo(g); i++) { anguloSuave = g; delay(10); }
    anguloZero = anguloSuave;
  }
  ultimoParaEstabilidade = anguloSuave;
  desdeQuandoParado = millis();

  WiFi.mode(WIFI_AP);
  WiFi.softAP(REDE_NOME, REDE_SENHA);
  Serial.print("Rede criada: ");  Serial.println(REDE_NOME);
  Serial.print("Endereco:    http://"); Serial.println(WiFi.softAPIP());

  servidor.on("/", rotaRaiz);
  servidor.on("/dados", rotaDados);
  servidor.on("/zerar", rotaZerar);
  servidor.begin();
}

void loop() {
  servidor.handleClient();

  float g;
  if (sensorOk && lerAngulo(g)) {
    anguloSuave += (g - anguloSuave) * SUAVIZACAO;      // média móvel: tira o tremor da mão

    if (fabs(anguloSuave - ultimoParaEstabilidade) > TOLERANCIA_ESTAVEL) {
      ultimoParaEstabilidade = anguloSuave;
      desdeQuandoParado = millis();                     // mexeu: reinicia a contagem de "parado"
    }
  }
  delay(12);
}
