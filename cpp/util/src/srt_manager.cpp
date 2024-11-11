#include "srt_manager.h"
#include <srt/srt.h>
#include <iostream>

SRTManager::SRTManager(){
    srt_startup();
}

SRTManager::~SRTManager(){
    srt_cleanup();
}

int SRTManager::create_socket(){
    SRTManager::socket = srt_create_socket();
    if (SRTManager::socket == SRT_INVALID_SOCK) {
        std::cerr << "Error creating SRT socket: " << srt_getlasterror_str() << std::endl;
        return -1;
    }
    return 0;
}

int SRTManager::connect(){
    struct sockaddr_in recv_addr;
    recv_addr.sin_family = AF_INET;
    recv_addr.sin_port = htons(4200);
    inet_aton("127.0.0.1", &(recv_addr.sin_addr));

    if (SRT_ERROR == srt_connect(SRTManager::socket, (struct sockaddr*)&recv_addr, sizeof(recv_addr)))
    {
        int rej = srt_getrejectreason(SRTManager::socket);
        std::cout << "connect: " << srt_getlasterror_str() << ":" << srt_rejectreason_str(rej) << std::endl;
        return -1;
    }
}

void SRTManager::send_data(){
    while (true)
    {
        const char* data = "Your data here";
        int nsnd = srt_send(SRTManager::socket, data, strlen(data));
        if (nsnd == SRT_ERROR)
       {
           std::cout << "SRT ERROR: " << srt_getlasterror_str() << std::endl;
           break;
       }
    }  
}

