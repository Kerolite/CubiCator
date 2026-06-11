#include <Arduino.h>
#include <Servo.h>

// ------------------------------------------------------------------------------
// RAIL : 0 = dégagé, 180 = engagé
// CLAW : 90 = neutre, 0 = rotation sens A, 180 = rotation sens B
// ------------------------------------------------------------------------------
#define ENGAGED   180
#define DISENGAGED 0
#define NEUTRAL    90
#define CW         0    // Clockwise
#define CCW        180  // Counter-clockwise

// Moves doubles et triples encodés comme chars uniques
#define U2 '1'
#define D2 '2'
#define R2 '3'
#define L2 '4'

// Index des servos
#define UP    0
#define DOWN  1
#define RIGHT 2
#define LEFT  3

// ------------------------------------------------------------------------------
// PINS — à modifier selon ton câblage
// ------------------------------------------------------------------------------
#define PIN_RAIL_UP     9   // sliders UP-DOWN partagés
#define PIN_RAIL_DOWN   9   // sliders UP-DOWN partagés

#define PIN_RAIL_RIGHT  3   // sliders LEFT-RIGHT partagés
#define PIN_RAIL_LEFT   3   // sliders LEFT-RIGHT partagés

#define PIN_CLAW_UP     10
#define PIN_CLAW_DOWN   11

#define PIN_CLAW_RIGHT  5
#define PIN_CLAW_LEFT   6

Servo rail[4];  // rail[UP], rail[DOWN], rail[RIGHT], rail[LEFT]
Servo claw[4];  // claw[UP], claw[DOWN], claw[RIGHT], claw[LEFT]

String moves="";
char normalised[200];
int  normalised_len=0;
bool received=false;


// ------------------------------------------------------------------------------
// UTILITAIRES
// ------------------------------------------------------------------------------

void engage(int axis){
  rail[axis].write(ENGAGED);
}

void disengage(int axis){
  rail[axis].write(DISENGAGED);
}

void neutral(int axis){
  claw[axis].write(NEUTRAL);
}

void all_neutral(){
  // Remet toutes les claws à 90° puis engage — position de repos
  // neutral() AVANT engage() pour ne pas tourner une face en s'engageant
  for(int i=0; i<4; i++){
    neutral(i);
    delay(300);
    engage(i);
  }
}


// ------------------------------------------------------------------------------
// NORMALIZE
// Remplace les moves F et B par un T (rotation cube UP→FRONT) suivi d'un
// move U ou D équivalent, et met à jour toutes les faces suivantes.
// Ensuite compacte les répétitions : XX → X2, XXX → x (anti-horaire).
// Retourne la longueur du tableau normalised[].
// ------------------------------------------------------------------------------

int normalize(String m){
  char tmp[200];
  int len=m.length();

  // Copie initiale dans tmp
  for(int i=0; i<len; i++) tmp[i]=m[i];

  // --- Partie 1 : remplacement F/B par T + substitution des faces suivantes ---
  char buf[200];
  int k=0;
  for(int i=0; i<len; i++){
    if(tmp[i]=='F' || tmp[i]=='B'){
      buf[k++]='T';
      // On substitue toutes les faces à partir de i+1
      for(int j=i+1; j<len; j++){
        switch(tmp[j]){
          case 'U': tmp[j]='F'; break;
          case 'D': tmp[j]='B'; break;
          case 'F': tmp[j]='D'; break;
          case 'B': tmp[j]='U'; break;
        }
      }
      // Le move F devient U, le move B devient D après rotation
      buf[k++]=(tmp[i]=='F') ? 'U' : 'D';
    }
    else{
      buf[k++]=tmp[i];
    }
  }
  len=k;

  // --- Partie 2 : compactage des répétitions (XX→X2, XXX→x) ---
  int j=0;
  int i=0;
  while(i<len){
    if(i+2 < len && buf[i]==buf[i+1] && buf[i+1]==buf[i+2]){
      // 3 moves identiques → move anti-horaire (minuscule)
      switch(buf[i]){
        case 'U': normalised[j++]='u'; break;
        case 'D': normalised[j++]='d'; break;
        case 'R': normalised[j++]='r'; break;
        case 'L': normalised[j++]='l'; break;
        default:  normalised[j++]=buf[i]; break;
      }
      i+=3;
    }
    else if(i+1 < len && buf[i]==buf[i+1]){
      // 2 moves identiques → move double
      switch(buf[i]){
        case 'U': normalised[j++]=U2; break;
        case 'D': normalised[j++]=D2; break;
        case 'R': normalised[j++]=R2; break;
        case 'L': normalised[j++]=L2; break;
        default:  normalised[j++]=buf[i]; break;
      }
      i+=2;
    }
    else{
      normalised[j++]=buf[i++];
    }
  }
  return j;
}


// ------------------------------------------------------------------------------
// EXECUTE MOVE
// ------------------------------------------------------------------------------

void doSimpleMove(int axis, int direction){
  // Séquence pour un move simple (90°) sur un axe donné :
  // Les deux claws de l'axe perpendiculaire restent engagées à 90°
  // pour maintenir le cube pendant la rotation.
  int perp_a=(axis==UP || axis==DOWN) ? RIGHT : UP;
  int perp_b=(axis==UP || axis==DOWN) ? LEFT  : DOWN;

  neutral(perp_a);  engage(perp_a);    // Maintien : neutral() avant engage() pour ne pas tourner
  neutral(perp_b);  engage(perp_b);

  disengage(axis);                      // Libérer l'axe actif le temps de se positionner
  // (l'autre claw de l'axe actif n'existe pas, UP/DOWN sont indépendants de RIGHT/LEFT)

  engage(axis);                         // Engager la claw active
  delay(300);
  claw[axis].write(direction);          // Tourner
  delay(500);
  disengage(axis);                      // Dégager
  delay(300);
  neutral(axis);                        // Revenir à 90°
  delay(300);
  engage(axis);                         // Réengager en position neutre
  delay(200);
}

void doDoubleMove(int axis){
  // Move double (180°) : on s'engage depuis un extrême et on tourne à 180°
  // Le sens importe peu pour un 180°, on choisit CW par convention
  int perp_a=(axis==UP || axis==DOWN) ? RIGHT : UP;
  int perp_b=(axis==UP || axis==DOWN) ? LEFT  : DOWN;

  neutral(perp_a);  engage(perp_a);    // neutral() avant engage()
  neutral(perp_b);  engage(perp_b);

  claw[axis].write(CW);                 // Se positionner à l'extrême avant d'engager
  delay(300);
  engage(axis);
  delay(300);
  claw[axis].write(CCW);               // Rotation 180° depuis l'extrême
  delay(600);
  disengage(axis);
  delay(300);
  neutral(axis);
  delay(300);
  engage(axis);
  delay(200);
}

void doTurn(){
  // Rotation du cube entier : UP→FRONT
  // UP et DOWN dégagées, RIGHT et LEFT engagées tournent ensemble
  disengage(UP);
  disengage(DOWN);
  delay(300);

  engage(RIGHT);  engage(LEFT);
  delay(200);

  claw[RIGHT].write(CW);   // Les deux tournent dans le même sens physique
  claw[LEFT].write(CW);    // (montage opposé → mouvement coordonné UP→FRONT)
  delay(600);

  disengage(RIGHT);  disengage(LEFT);
  delay(300);

  neutral(RIGHT);  neutral(LEFT);
  delay(300);

  // Retour position repos : toutes engagées à 90°
  all_neutral();
  delay(200);
}

void executeMove(char m){
  switch(m){
    case 'U':  doSimpleMove(UP,    CW);  break;
    case 'u':  doSimpleMove(UP,    CCW); break;
    case U2:   doDoubleMove(UP);         break;
    case 'D':  doSimpleMove(DOWN,  CW);  break;
    case 'd':  doSimpleMove(DOWN,  CCW); break;
    case D2:   doDoubleMove(DOWN);       break;
    case 'R':  doSimpleMove(RIGHT, CW);  break;
    case 'r':  doSimpleMove(RIGHT, CCW); break;
    case R2:   doDoubleMove(RIGHT);      break;
    case 'L':  doSimpleMove(LEFT,  CW);  break;
    case 'l':  doSimpleMove(LEFT,  CCW); break;
    case L2:   doDoubleMove(LEFT);       break;
    case 'T':  doTurn();                 break;
  }
}


// ------------------------------------------------------------------------------
// SCAN DU CUBE : rotation pour exposer les 6 faces à la caméra
// Séquence définie selon l'ordre U/R/F/D/L/B de Kociemba
// ------------------------------------------------------------------------------

void scanRotation(int i){
  // Entre chaque face scannée, on tourne le cube pour exposer la suivante.
  // Séquence : après U → tourner pour exposer R → F → D → L → B
  switch(i){
    case 0: doSimpleMove(RIGHT, CW);  break;  // U scanné → exposer R (tilt vers la droite)
    case 1: doTurn();                 break;  // R scanné → exposer F
    case 2: doSimpleMove(RIGHT, CCW); break;  // F scanné → exposer D
    case 3: doTurn();                 break;  // D scanné → exposer L
    case 4: doTurn();                 break;  // L scanné → exposer B
    // i==5 : B scanné → scan terminé, pas de rotation
  }
}


// ------------------------------------------------------------------------------
// HARD RESET
// ------------------------------------------------------------------------------

void hard_reset(){
  // ONLY USE WHEN UNEXPECTED CASE HAPPENED OR FOR FINAL RESET
  disengage(UP);    neutral(UP);
  disengage(DOWN);  neutral(DOWN);
  disengage(RIGHT); neutral(RIGHT);
  disengage(LEFT);  neutral(LEFT);
  delay(500);
  all_neutral();
}


// ------------------------------------------------------------------------------
// SETUP / LOOP
// ------------------------------------------------------------------------------

void setup(){
  rail[UP].attach(PIN_RAIL_UP);
  rail[DOWN].attach(PIN_RAIL_DOWN);
  rail[RIGHT].attach(PIN_RAIL_RIGHT);
  rail[LEFT].attach(PIN_RAIL_LEFT);
  claw[UP].attach(PIN_CLAW_UP);
  claw[DOWN].attach(PIN_CLAW_DOWN);
  claw[RIGHT].attach(PIN_CLAW_RIGHT);
  claw[LEFT].attach(PIN_CLAW_LEFT);
  Serial.begin(9600);

  engage(RIGHT);
  engage(LEFT);
  claw[RIGHT].write(0);
  claw[LEFT].write(0);
  claw[UP].write(0);
  claw[DOWN].write(0);
  delay(2000);
  disengage(RIGHT);
  disengage(LEFT);
  claw[RIGHT].write(180);
  claw[LEFT].write(180);
  claw[UP].write(180);
  claw[DOWN].write(180);
}

void loop(){
  received = false;
  moves = "";
  hard_reset();
  all_neutral();

  // --- Phase 1 : scan des 6 faces ---
  for(int i=0; i<6; i++){
    while(1){
      if(Serial.available()){
        String cmd=Serial.readStringUntil('\n');
        cmd.trim();
        if(cmd=="NEXT"){
          if(i < 5) scanRotation(i);   // Tourner pour exposer la face suivante
          Serial.println("OK");
          break;
        }
      }
    }
  }

  // --- Phase 2 : réception de la séquence de moves ---
  Serial.println("READY");
  while(!received){
    if(Serial.available()){
      moves=Serial.readStringUntil('\n');
      moves.trim();
      Serial.println("OK");
      received=true;
    }
  }

  // --- Phase 3 : normalisation + exécution ---
  normalised_len=normalize(moves);
  for(int i=0; i<normalised_len; i++){
    executeMove(normalised[i]);
  }

  hard_reset();
}