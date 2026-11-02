#include <stdio.h>
#include "protocol.h"
#include <sys/time.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>


int main(){

  int sockfd;
  sockfd=socket(AF_INET, SOCK_DGRAM, 0);

  if(sockfd<0) return 1;

  struct sockaddr_in server_addr;
  memset( &server_addr,0,sizeof(struct sockaddr_in));

  server_addr.sin_family = AF_INET;
  server_addr.sin_port=htons(8000);
  server_addr.sin_addr.s_addr=INADDR_ANY;

  int a=bind(sockfd,(struct sockaddr *) &server_addr,sizeof(struct sockaddr_in));
  if(a<0) return 1;
  int expected_seq=0;

  struct packet pkt;
  struct sockaddr_in sender;
  socklen_t sender_len = sizeof(sender);

  char name[256];
  FILE *fp=NULL;

  int fin_received=0;


  while(1){
    int n=recvfrom(sockfd,&pkt,sizeof(pkt),0,(struct sockaddr*) &sender,&sender_len);
    if(n<0){
      if(fin_received && (errno==EAGAIN || errno == EWOULDBLOCK)){
        printf("FIN waiting complele\n");
        break;
      }
      perror("recvfrom");
      return 1;
    }

    struct ack ack;

    if(pkt.type ==TYPE_H){
      if(pkt.sequence_number == expected_seq){
        strcpy(name,pkt.data);
        char output_name[300];
        snprintf(output_name,sizeof(output_name),"received_%s",name);
        fp=fopen(output_name,"wb");
        if(fp==NULL){
          perror("file opening");
          return 1;
        }
        expected_seq++;
        ack.sequence_number=pkt.sequence_number;
        sendto(sockfd,&ack,sizeof(ack),0,(struct sockaddr *)& sender,sender_len);
      }
      else if(pkt.sequence_number< expected_seq){
        ack.sequence_number=pkt.sequence_number;
        sendto(sockfd,&ack,sizeof(ack),0,(struct sockaddr *)& sender,sender_len);
      }
      continue;
    }

    if(pkt.type==TYPE_F) {
      printf("End of file being sent");
      ack.sequence_number=pkt.sequence_number;
      sendto(sockfd,&ack,sizeof(ack),0,(struct sockaddr*)&sender,sender_len);
      printf("FIN Received, ACK sent\n");

      if(!fin_received){
        fin_received=1;

        struct timeval wait;
        wait.tv_sec=2;
        wait.tv_usec=0;

        setsockopt(sockfd,SOL_SOCKET,SO_RCVTIMEO,&wait,sizeof(wait));
      }
      continue;
    }

    else if(pkt.type==TYPE_D){
      if(expected_seq==pkt.sequence_number){
        printf("Received %dth packet of %d bytes\n",pkt.sequence_number,pkt.length);
        fwrite(pkt.data,1,pkt.length,fp);
        expected_seq++;
      }

      else if(expected_seq > pkt.sequence_number){
        printf("Received duplicate packet.. discarding\n");
      }
      else{
        printf("unexpected packet");
        continue;
      }

      ack.sequence_number=pkt.sequence_number;
      sendto(sockfd,&ack,sizeof(ack),0,(struct sockaddr * )& sender,sender_len);
    }
  }
  fclose(fp);
  close(sockfd);


}
